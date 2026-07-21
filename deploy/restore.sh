#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
ARCHIVE_IMAGE="${ARCHIVE_IMAGE:-alpine:3.21.3}"
FORCE=0
START_STACK=0

usage() {
  echo "Usage: $0 [--force] [--start] BACKUP_DIRECTORY" >&2
  echo "  --force  remove and recreate existing data volumes (destructive)" >&2
  echo "  --start  start the complete stack after a successful restore" >&2
}

while (( $# > 0 )); do
  case "$1" in
    --force) FORCE=1 ;;
    --start) START_STACK=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) usage; exit 2 ;;
    *)
      if [[ -n "${BACKUP_DIR:-}" ]]; then usage; exit 2; fi
      BACKUP_DIR="$(cd "$1" && pwd)"
      ;;
  esac
  shift
done

if [[ -z "${BACKUP_DIR:-}" ]] || [[ ! -d "$BACKUP_DIR" ]]; then
  usage
  exit 2
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing production environment file: $ENV_FILE" >&2
  exit 1
fi
for file in postgres.dump uploads_data.tgz minio_data.tgz; do
  if [[ ! -f "$BACKUP_DIR/$file" ]]; then
    echo "Missing backup artifact: $BACKUP_DIR/$file" >&2
    exit 1
  fi
done
if [[ ! -f "$BACKUP_DIR/SHA256SUMS" ]]; then
  echo "Missing required backup checksum manifest: $BACKUP_DIR/SHA256SUMS" >&2
  exit 1
fi
if ! command -v sha256sum >/dev/null 2>&1; then
  echo "sha256sum is required before restoring a production backup." >&2
  exit 1
fi
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/compose.prod.yml")
COMPOSE_CONFIG="$("${COMPOSE[@]}" config)"
PROJECT_NAME="$(printf '%s\n' "$COMPOSE_CONFIG" | awk '$1 == "name:" { gsub(/[\"\047]/, "", $2); print $2; exit }')"

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

if [[ -n "$("${COMPOSE[@]}" ps --services --status running)" ]]; then
  echo "Refusing to restore while Compose services are running. Stop the stack first." >&2
  exit 1
fi

prepare_empty_volume() {
  local logical_name="$1"
  local volume_name
  volume_name="$(resolve_volume "$logical_name")"
  if [[ -z "$volume_name" ]]; then
    echo "Unable to resolve volume name for $logical_name." >&2
    exit 1
  fi
  if docker volume inspect "$volume_name" >/dev/null 2>&1; then
    if (( FORCE == 0 )); then
      echo "Volume $volume_name already exists. Re-run with --force only after verifying the backup." >&2
      exit 1
    fi
    docker volume rm "$volume_name" >/dev/null
  fi
  docker volume create \
    --label "com.docker.compose.project=$PROJECT_NAME" \
    --label "com.docker.compose.volume=$logical_name" \
    "$volume_name" >/dev/null
  printf '%s' "$volume_name"
}

restore_archive() {
  local logical_name="$1"
  local volume_name="$2"
  docker run --rm \
    --mount "type=volume,src=$volume_name,dst=/data" \
    --mount "type=bind,src=$BACKUP_DIR,dst=/backup,readonly" \
    "$ARCHIVE_IMAGE" tar xzf "/backup/$logical_name.tgz" -C /data
}

UPLOADS_VOLUME="$(prepare_empty_volume uploads_data)"
MINIO_VOLUME="$(prepare_empty_volume minio_data)"
REDIS_VOLUME="$(prepare_empty_volume redis_data)"
POSTGRES_VOLUME="$(prepare_empty_volume postgres_data)"

restore_archive uploads_data "$UPLOADS_VOLUME"
restore_archive minio_data "$MINIO_VOLUME"
# Redis is an operational Celery broker/cache, not authoritative business
# storage. Keep the newly created volume empty so stale queued work cannot be
# replayed after a migration or disaster recovery.
: "$REDIS_VOLUME"

echo "Starting PostgreSQL temporarily for logical restore..."
POSTGRES_STARTED=1

stop_temporary_postgres() {
  if (( ${POSTGRES_STARTED:-0} == 1 )); then
    "${COMPOSE[@]}" stop postgres >/dev/null || true
  fi
}
trap stop_temporary_postgres EXIT
"${COMPOSE[@]}" up -d postgres

ready=0
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T postgres sh -c \
    'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if (( ready == 0 )); then
  echo "PostgreSQL did not become ready in time." >&2
  exit 1
fi

cat "$BACKUP_DIR/postgres.dump" | "${COMPOSE[@]}" exec -T postgres sh -c \
  'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

if (( START_STACK == 1 )); then
  POSTGRES_STARTED=0
  trap - EXIT
  "${COMPOSE[@]}" up -d
  echo "Restore complete; the full stack has been started."
else
  "${COMPOSE[@]}" stop postgres
  POSTGRES_STARTED=0
  trap - EXIT
  echo "Restore complete; all services remain stopped. Run the production Compose command when ready."
fi
