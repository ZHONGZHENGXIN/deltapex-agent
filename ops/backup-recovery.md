# tracoach Backup And Recovery Runbook

## Scope

- Postgres is the source of truth and must have daily custom-format dumps retained for 30 days.
- Redis is cache/ephemeral state. It may be discarded during recovery unless P2-4 adds durable rate-limit or queue state.
- one-api channel/config must be exported weekly with secrets redacted and retained for 90 days.
- Provider keys are not backed up in plaintext. Store live keys in Zeabur environment variables and provider consoles.

## Required Environment

Set these values on the trusted ops host or Zeabur scheduled job:

```sh
POSTGRES_URL=postgresql://user:password@host:5432/dbname
POSTGRES_BACKUP_DIR=/secure-backups/tracoach/postgres
POSTGRES_BACKUP_RETENTION_DAYS=30

ONE_API_SQLITE_DB=/secure-mounted-one-api/one-api.db
ONE_API_CONFIG_BACKUP_DIR=/secure-backups/tracoach/one-api
ONE_API_CONFIG_RETENTION_DAYS=90
```

If `POSTGRES_URL` is not available, set `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and
`POSTGRES_DB`.

## Daily Postgres Backup

```sh
scripts/backup_postgres.sh
```

Output:

- `*.dump`: `pg_dump --format=custom --no-owner`
- `*.dump.sha256`: checksum
- `*.dump.manifest`: restore metadata

The compose deployments include a `postgres-backup` sidecar as a visible backup task. On Zeabur, use either Zeabur's
scheduled-job equivalent or an external ops host running `ops/crontab.example` against the Zeabur PostgreSQL connection.

## Weekly one-api Config Export

```sh
python3 scripts/export_one_api_config.py
```

The export redacts secret-like fields, `Bearer` tokens, `sk-*` values, emails, and binary values. If one-api is configured
with an external SQL database instead of local SQLite, export that database through the database backup mechanism and keep
this script as the redacted metadata snapshot.

## Restore To Staging

Never restore into production during a rehearsal.

```sh
export TARGET_POSTGRES_URL=postgresql://staging_user:password@staging-host:5432/staging_db
export POSTGRES_DB=staging_db
export BACKUP_FILE=/secure-backups/tracoach/postgres/prod_20260505T020000Z.dump
export RESTORE_CONFIRM=restore-staging_db
scripts/restore_postgres.sh
```

After restore:

1. Run Alembic current in the staging API container: `python -m alembic current`.
2. Start staging API and verify `/health`.
3. Log in with a test user.
4. Open chat list and verify restored chats/messages are present.
5. Verify no provider key appears in API responses or logs.
6. Run `python3 scripts/export_one_api_config.py` and verify the JSON contains redacted config only.
7. Fill `ops/recovery-rehearsal-log.md`.

## Recovery Targets

- Backup frequency: daily Postgres dump.
- Retention: 30 days for Postgres dumps, 90 days for one-api redacted exports.
- RPO target: 24 hours.
- RTO target for staging restore rehearsal: 2 hours.

## Zeabur Notes

- The current production database is Zeabur PostgreSQL, not Supabase.
- Keep Zeabur database credentials and provider keys out of git.
- If Zeabur built-in backups are enabled, keep them enabled in addition to these dumps.
- If a restore is required, restore to a new staging database first, run smoke checks, then plan a production cutover.
