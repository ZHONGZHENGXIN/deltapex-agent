from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_postgres_backup_and_restore_scripts_exist():
    backup = read("scripts/backup_postgres.sh")
    restore = read("scripts/restore_postgres.sh")

    assert "pg_dump" in backup
    assert "--format=custom" in backup
    assert "POSTGRES_BACKUP_RETENTION_DAYS" in backup
    assert "sha256" in backup

    assert "pg_restore" in restore
    assert "--clean" in restore
    assert "--if-exists" in restore
    assert "RESTORE_CONFIRM" in restore


def test_one_api_config_export_redacts_secrets():
    exporter = read("scripts/export_one_api_config.py")

    assert "one-api" in exporter
    assert "redact_value" in exporter
    assert "SENSITIVE_KEY_RE" in exporter
    assert "ONE_API_CONFIG_RETENTION_DAYS" in exporter
    assert "sha256" in exporter


def test_compose_files_have_visible_backup_task_config():
    prod_compose = read("deploy/docker-compose.yaml")
    test_compose = read("deploy-test/docker-compose.yaml")

    for compose in (prod_compose, test_compose):
        assert "postgres-backup" in compose
        assert "POSTGRES_BACKUP_RETENTION_DAYS" in compose
        assert "POSTGRES_BACKUP_INTERVAL_SECONDS" in compose
        assert "pg_dump" in compose
        assert "volumes/backups/postgres" in compose


def test_ops_runbook_and_rehearsal_log_exist():
    runbook = read("ops/backup-recovery.md")
    rehearsal_log = read("ops/recovery-rehearsal-log.md")
    crontab = read("ops/crontab.example")

    assert "Zeabur PostgreSQL" in runbook
    assert "Restore To Staging" in runbook
    assert "RPO target: 24 hours" in runbook
    assert "RTO target" in runbook
    assert "scripts/backup_postgres.sh" in crontab
    assert "scripts/export_one_api_config.py" in crontab
    assert "Template" in rehearsal_log
