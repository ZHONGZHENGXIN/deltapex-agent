#!/usr/bin/env sh
set -eu

BACKUP_DIR="${POSTGRES_BACKUP_DIR:-${BACKUP_DIR:-./backups/postgres}}"
RETENTION_DAYS="${POSTGRES_BACKUP_RETENTION_DAYS:-${BACKUP_RETENTION_DAYS:-30}}"
TIMESTAMP="${BACKUP_TIMESTAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
DB_LABEL="${POSTGRES_DB:-postgres}"
BACKUP_FILE="${BACKUP_DIR}/${DB_LABEL}_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump is required but was not found" >&2
  exit 127
fi

if [ -n "${POSTGRES_URL:-}" ]; then
  pg_dump "$POSTGRES_URL" --format=custom --no-owner --file "$BACKUP_FILE"
else
  POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
  POSTGRES_PORT="${POSTGRES_PORT:-5432}"
  POSTGRES_USER="${POSTGRES_USER:-postgres}"
  POSTGRES_DB="${POSTGRES_DB:-postgres}"
  export PGPASSWORD="${POSTGRES_PASSWORD:-${PGPASSWORD:-}}"

  pg_dump \
    --host "$POSTGRES_HOST" \
    --port "$POSTGRES_PORT" \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --format=custom \
    --no-owner \
    --file "$BACKUP_FILE"
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
else
  echo "sha256 tool not found; backup created without checksum" >&2
fi

cat > "${BACKUP_FILE}.manifest" <<EOF
backup_file=$(basename "$BACKUP_FILE")
created_at_utc=$TIMESTAMP
retention_days=$RETENTION_DAYS
postgres_host=${POSTGRES_HOST:-url}
postgres_db=${POSTGRES_DB:-url}
format=pg_dump_custom
restore_command=RESTORE_CONFIRM=restore-\${POSTGRES_DB:-target} BACKUP_FILE=$BACKUP_FILE scripts/restore_postgres.sh
EOF

find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.dump.sha256" -o -name "*.dump.manifest" \) \
  -mtime +"$RETENTION_DAYS" -delete

echo "Postgres backup created: $BACKUP_FILE"
