#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
ARCHIVE_IMAGE="${ARCHIVE_IMAGE:-alpine:3.21.3}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_ROOT/$STAMP"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 1
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/compose.prod.yml")
COMPOSE_CONFIG="$("${COMPOSE[@]}" config)"
PROJECT_NAME="$(printf '%s\n' "$COMPOSE_CONFIG" | awk '$1 == "name:" { gsub(/[\"\047]/, "", $2); print $2; exit }')"

if [[ -z "$PROJECT_NAME" ]]; then
  echo "Unable to resolve the Compose project name." >&2
  exit 1
fi

resolve_volume() {
  local logical_name="$1"
  printf '%s\n' "$COMPOSE_CONFIG" | awk -v key="$logical_name" '
    $0 == "volumes:" { in_volumes=1; next }
    in_volumes && $0 !~ /^ / { exit }
    in_volumes && $0 == "  " key ":" { found=1; next }
    found && $1 == "name:" { gsub(/["\047]/, "", $2); print $2; exit }
    found && $0 ~ /^  [^ ]/ { exit }
  '
}

archive_volume() {
  local logical_name="$1"
  local volume_name
  volume_name="$(resolve_volume "$logical_name")"
  if [[ -z "$volume_name" ]] || ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
    echo "Required volume for $logical_name was not found (${volume_name:-unresolved})." >&2
    exit 1
  fi
  docker run --rm \
    --mount "type=volume,src=$volume_name,dst=/data,readonly" \
    --mount "type=bind,src=$BACKUP_DIR,dst=/backup" \
    "$ARCHIVE_IMAGE" tar czf "/backup/$logical_name.tgz" -C /data .
}

RUNNING_SERVICES="$("${COMPOSE[@]}" ps --services --status running)"
RESTART_SERVICES=()
# Dependency order gives a safer restart order after the snapshot.
for service in minio api worker web; do
  if printf '%s\n' "$RUNNING_SERVICES" | grep -qx "$service"; then
    RESTART_SERVICES+=("$service")
  fi
done

restart_quiesced_services() {
  if (( ${#RESTART_SERVICES[@]} > 0 )); then
    "${COMPOSE[@]}" start "${RESTART_SERVICES[@]}" >/dev/null
  fi
}
trap restart_quiesced_services EXIT

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# Keep only unexpanded source configuration and non-secret runtime metadata.
# `docker compose config` contains interpolated credentials and must never be
# persisted in a backup artifact.
install -m 600 "$ROOT_DIR/docker-compose.yml" "$BACKUP_DIR/docker-compose.yml"
install -m 600 "$ROOT_DIR/compose.prod.yml" "$BACKUP_DIR/compose.prod.yml"
{
  docker version --format 'Docker client={{.Client.Version}} server={{.Server.Version}}'
  docker compose version
  printf 'project=%s\n' "$PROJECT_NAME"
} > "$BACKUP_DIR/runtime-versions.txt"
"${COMPOSE[@]}" config --images | sort -u > "$BACKUP_DIR/service-images.txt"

# Stop every application entry point before taking either the database dump or
# attachment snapshots. This keeps PostgreSQL rows and file volumes at the same
# application-level point in time. PostgreSQL itself remains online for pg_dump.
QUIESCE_SERVICES=()
for service in web worker api; do
  if printf '%s\n' "$RUNNING_SERVICES" | grep -qx "$service"; then
    QUIESCE_SERVICES+=("$service")
  fi
done
if (( ${#QUIESCE_SERVICES[@]} > 0 )); then
  echo "Entering maintenance window; stopping web, worker and API writers..."
  "${COMPOSE[@]}" stop "${QUIESCE_SERVICES[@]}"
fi

echo "Writing PostgreSQL logical backup after writers are stopped..."
"${COMPOSE[@]}" exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP_DIR/postgres.dump"

VOLUME_SERVICES=()
for service in minio; do
  if printf '%s\n' "$RUNNING_SERVICES" | grep -qx "$service"; then
    VOLUME_SERVICES+=("$service")
  fi
done
if (( ${#VOLUME_SERVICES[@]} > 0 )); then
  echo "Stopping MinIO for a consistent object-storage snapshot..."
  "${COMPOSE[@]}" stop "${VOLUME_SERVICES[@]}"
fi

archive_volume uploads_data
archive_volume minio_data

if ! command -v sha256sum >/dev/null 2>&1; then
  echo "sha256sum is required to create a verifiable production backup." >&2
  exit 1
fi
(cd "$BACKUP_DIR" && sha256sum \
  docker-compose.yml compose.prod.yml runtime-versions.txt service-images.txt \
  postgres.dump uploads_data.tgz minio_data.tgz > SHA256SUMS)
chmod 600 "$BACKUP_DIR"/*

trap - EXIT
restart_quiesced_services

echo "Backup complete: $BACKUP_DIR"
echo "No expanded Compose configuration or environment file was copied."
echo "Back up $ENV_FILE separately using encrypted storage."
