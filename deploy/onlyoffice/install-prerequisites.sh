#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

fail() { printf 'ONLYOFFICE_PREREQUISITES_FAILED: %s\n' "$1" >&2; exit 1; }
[[ "$EUID" -eq 0 ]] || fail 'root is required'
for key in DOCKER_CE_VERSION DOCKER_CONTAINERD_VERSION DOCKER_COMPOSE_VERSION DOCKER_APT_KEY_SHA256 ONLYOFFICE_SWAP_FILE ONLYOFFICE_RUNTIME_DIR; do
  [[ -n "${!key:-}" ]] || fail "missing configuration: $key"
done
[[ "$DOCKER_APT_KEY_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail 'invalid official signing key checksum'
[[ "$ONLYOFFICE_SWAP_FILE" =~ ^/[A-Za-z0-9_./-]+$ ]] || fail 'invalid swap path'
[[ "$ONLYOFFICE_RUNTIME_DIR" =~ ^/[A-Za-z0-9_./-]+$ ]] || fail 'invalid runtime path'
. /etc/os-release
[[ "$ID" == ubuntu && -n "$VERSION_CODENAME" ]] || fail 'only official Ubuntu packages are supported'

# 不卸载、升级或重启既有组件；冲突交给部署负责人处理。
for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
  if status="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null)"; then
    [[ "$status" != installed ]] || fail "existing package conflicts: $package"
  elif [[ "$?" -ne 1 ]]; then
    fail "unable to inspect package: $package"
  fi
done
command -v curl >/dev/null || fail 'curl must already be installed'
command -v gpg >/dev/null || fail 'gpg must already be installed'
install -d -m 0700 "$ONLYOFFICE_RUNTIME_DIR/backups"
exec 9>"$ONLYOFFICE_RUNTIME_DIR/prerequisites.lock"
flock -n 9 || fail 'another prerequisite installation is running'

key_file=/etc/apt/keyrings/sunhold-onlyoffice-docker.asc
source_file=/etc/apt/sources.list.d/sunhold-onlyoffice-docker.sources
install -d -m 0755 /etc/apt/keyrings
if [[ ! -f "$key_file" ]]; then
  key_tmp="$(mktemp)"
  trap 'rm -f -- "$key_tmp"' EXIT
  curl -4 --fail --silent --show-error --connect-timeout 10 --max-time 30 \
    https://download.docker.com/linux/ubuntu/gpg -o "$key_tmp"
  printf '%s  %s\n' "$DOCKER_APT_KEY_SHA256" "$key_tmp" | sha256sum -c - >/dev/null
  gpg --batch --show-keys "$key_tmp" >/dev/null
  install -m 0644 "$key_tmp" "$key_file"
fi
printf '%s  %s\n' "$DOCKER_APT_KEY_SHA256" "$key_file" | sha256sum -c - >/dev/null
source_text="$(printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: %s\n' "$VERSION_CODENAME" "$(dpkg --print-architecture)" "$key_file")"
if [[ -e "$source_file" ]]; then
  [[ "$(<"$source_file")" == "$source_text" ]] || fail 'existing source configuration differs'
else
  printf '%s\n' "$source_text" > "$source_file"
  chmod 0644 "$source_file"
fi

packages=("docker-ce=$DOCKER_CE_VERSION" "docker-ce-cli=$DOCKER_CE_VERSION"
  "containerd.io=$DOCKER_CONTAINERD_VERSION" "docker-compose-plugin=$DOCKER_COMPOSE_VERSION")
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
apt-get -o Acquire::ForceIPv4=true -o APT::Update::Error-Mode=any update
plan="$(apt-get --simulate --no-install-recommends --no-upgrade install "${packages[@]}")"
[[ "$plan" != *$'\nRemv '* ]] || fail 'installation would remove existing packages'
while read -r action package _; do
  [[ "$action" == Inst ]] || continue
  if installed="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null)"; then
    [[ "$installed" != installed ]] || fail "installation would change an existing package: $package"
  elif [[ "$?" -ne 1 ]]; then
    fail "unable to inspect package: $package"
  fi
done <<< "$plan"
apt-get -y --no-install-recommends --no-upgrade -o Acquire::ForceIPv4=true \
  -o Dpkg::Options::=--force-confold install "${packages[@]}"
systemctl enable --now docker.service
docker info --format 'DOCKER_READY: {{.ServerVersion}}'

# 只增加专属 swap；既有 swap 与 fstab 的其他条目保持原样。
swap="$ONLYOFFICE_SWAP_FILE"
size=4294967296
entry="$swap none swap sw 0 0 # sunhold-onlyoffice"
existing_entry="$(awk -v path="$swap" '$1 == path {print}' /etc/fstab)"
[[ -z "$existing_entry" || "$existing_entry" == "$entry" ]] || fail 'existing fstab swap entry differs'
if [[ -e "$swap" ]]; then
  [[ -f "$swap" && ! -L "$swap" && "$(stat -c %s "$swap")" == "$size" ]] || fail 'existing swap path is not the expected dedicated file'
  [[ "$(blkid -s TYPE -o value "$swap")" == swap ]] || fail 'existing file is not swap'
  [[ "$(blkid -s LABEL -o value "$swap")" == sunhold-office ]] || fail 'existing swap is not owned by this component'
  [[ "$(stat -c %a "$swap")" == 600 ]] || fail 'dedicated swap permissions must be 0600'
else
  [[ "$(df --output=avail -B1 "$(dirname "$swap")" | tail -n 1)" -gt 8589934592 ]] || fail 'insufficient space for dedicated swap'
  install -m 0600 /dev/null "$swap"
  fallocate -l "$size" "$swap"
  mkswap -L sunhold-office "$swap" >/dev/null
fi
if ! swapon --show=NAME --noheadings | grep -Fxq -- "$swap"; then
  swapon "$swap"
fi
if [[ -z "$existing_entry" ]]; then
  cp --preserve=all --no-clobber /etc/fstab "$ONLYOFFICE_RUNTIME_DIR/backups/fstab.$(date -u +%Y%m%dT%H%M%SZ)"
  printf '\n%s\n' "$entry" >> /etc/fstab
fi
printf 'ONLYOFFICE_PREREQUISITES_OK: official Docker and dedicated 4 GiB swap; no host reboot requested.\n'
