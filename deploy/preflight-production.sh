#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.env.production}"
PROD_COMPOSE="$ROOT_DIR/compose.prod.yml"
BASE_COMPOSE="$ROOT_DIR/compose.yaml"
[[ -f "$BASE_COMPOSE" ]] || BASE_COMPOSE="$ROOT_DIR/docker-compose.yml"

fail() {
  printf 'PRODUCTION_PREFLIGHT_FAILED: %s\n' "$1" >&2
  exit 1
}

[[ -f "$ENV_FILE" ]] || fail 'production environment file is missing'
[[ -f "$BASE_COMPOSE" ]] || fail 'base Compose file is missing'
[[ -f "$PROD_COMPOSE" ]] || fail 'production Compose file is missing'
command -v docker >/dev/null 2>&1 || fail 'docker command is unavailable'

mode="$(stat -c '%a' "$ENV_FILE" 2>/dev/null)" || fail 'unable to inspect environment file permissions'
[[ "$mode" =~ ^[0-7]{3,4}$ ]] || fail 'environment file permissions are invalid'
perm=$((8#$mode))
if (( (perm & 0077) != 0 || (perm & 0100) != 0 )); then
  fail 'environment file permissions must not be wider than 600'
fi

declare -A values=()
while IFS= read -r raw || [[ -n "$raw" ]]; do
  raw="${raw%$'\r'}"
  [[ "$raw" =~ ^[[:space:]]*$ || "$raw" =~ ^[[:space:]]*# ]] && continue
  raw="${raw#export }"
  [[ "$raw" == *=* ]] || fail 'environment file contains an invalid assignment'
  key="${raw%%=*}"
  value="${raw#*=}"
  key="${key#"${key%%[![:space:]]*}"}"
  key="${key%"${key##*[![:space:]]}"}"
  [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || fail 'environment file contains an invalid key'
  if [[ ${#value} -ge 2 ]]; then
    first="${value:0:1}"; last="${value: -1}"
    if [[ ( "$first" == '"' && "$last" == '"' ) || ( "$first" == "'" && "$last" == "'" ) ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi
  values["$key"]="$value"
done < "$ENV_FILE"

required=(
  POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL
  REDIS_PASSWORD REDIS_URL SECRET_KEY
  INITIAL_ADMIN_USERNAME INITIAL_ADMIN_PASSWORD
  MINIO_ROOT_USER MINIO_ROOT_PASSWORD
)
for key in "${required[@]}"; do
  [[ -v "values[$key]" ]] || fail "required key is missing: $key"
  [[ -n "${values[$key]}" ]] || fail "required key is empty: $key"
  [[ "${values[$key]}" != *CHANGE_ME* ]] || fail "placeholder value is forbidden: $key"
done

(( ${#values[SECRET_KEY]} >= 64 )) || fail 'SECRET_KEY must contain at least 64 characters'
(( ${#values[INITIAL_ADMIN_PASSWORD]} >= 12 )) || fail 'INITIAL_ADMIN_PASSWORD must contain at least 12 characters'
admin_password_lower="$(printf '%s' "${values[INITIAL_ADMIN_PASSWORD]}" | tr '[:upper:]' '[:lower:]')"
case "$admin_password_lower" in
  20230616601|admin|password) fail 'INITIAL_ADMIN_PASSWORD uses a forbidden default' ;;
esac
(( ${#values[POSTGRES_PASSWORD]} >= 16 )) || fail 'POSTGRES_PASSWORD must contain at least 16 characters'
(( ${#values[REDIS_PASSWORD]} >= 16 )) || fail 'REDIS_PASSWORD must contain at least 16 characters'
(( ${#values[MINIO_ROOT_PASSWORD]} >= 20 )) || fail 'MINIO_ROOT_PASSWORD must contain at least 20 characters'

if ! grep -Eq "^[[:space:]]*SEED_DEMO_DATA:[[:space:]]*['\"]?false['\"]?[[:space:]]*$" "$PROD_COMPOSE"; then
  fail 'production Compose must fix SEED_DEMO_DATA to false'
fi
if grep -Eq '^[[:space:]]*SEED_DEMO_DATA:.*\$\{' "$PROD_COMPOSE"; then
  fail 'production Compose must not interpolate SEED_DEMO_DATA'
fi

if ! docker compose --env-file "$ENV_FILE" -f "$BASE_COMPOSE" -f "$PROD_COMPOSE" config --quiet >/dev/null 2>&1; then
  fail 'production Docker Compose configuration is invalid'
fi

printf 'PRODUCTION_PREFLIGHT_OK: environment policy and production Compose configuration passed.\n'
