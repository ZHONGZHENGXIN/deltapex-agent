#!/usr/bin/env sh
set -eu

BACKUP_FILE="${BACKUP_FILE:-${1:-}}"
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: BACKUP_FILE=/path/to/file.dump RESTORE_CONFIRM=restore-<target-db> scripts/restore_postgres.sh" >&2
  exit 64
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 66
fi

TARGET_DB="${POSTGRES_DB:-target}"
if [ "${RESTORE_CONFIRM:-}" != "restore-${TARGET_DB}" ]; then
  echo "Refusing restore. Set RESTORE_CONFIRM=restore-${TARGET_DB} to continue." >&2
  exit 65
fi

if ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_restore is required but was not found" >&2
  exit 127
fi

if [ -f "${BACKUP_FILE}.sha256" ] && command -v sha256sum >/dev/null 2>&1; then
  (cd "$(dirname "$BACKUP_FILE")" && sha256sum -c "$(basename "${BACKUP_FILE}.sha256")")
fi

if [ -n "${TARGET_POSTGRES_URL:-}" ]; then
  pg_restore --clean --if-exists --no-owner --single-transaction --dbname "$TARGET_POSTGRES_URL" "$BACKUP_FILE"
elif [ -n "${POSTGRES_URL:-}" ]; then
  pg_restore --clean --if-exists --no-owner --single-transaction --dbname "$POSTGRES_URL" "$BACKUP_FILE"
else
  POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
  POSTGRES_PORT="${POSTGRES_PORT:-5432}"
  POSTGRES_USER="${POSTGRES_USER:-postgres}"
  POSTGRES_DB="${POSTGRES_DB:-postgres}"
  export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD:-}}"

  pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --single-transaction \
    --host "$POSTGRES_HOST" \
    --port "$POSTGRES_PORT" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    "$BACKUP_FILE"
fi

echo "Postgres restore completed into target database: $TARGET_DB"
