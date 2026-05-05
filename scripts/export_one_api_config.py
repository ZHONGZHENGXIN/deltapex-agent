#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SENSITIVE_KEY_RE = re.compile(r"(key|secret|token|password|credential)", re.IGNORECASE)
SECRET_VALUE_RE = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/=-]+)", re.IGNORECASE)
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
EXPORT_TABLE_RE = re.compile(r"(channel|option|model|ability|group|quota)", re.IGNORECASE)
SKIP_TABLE_RE = re.compile(r"(log|user|token|session)", re.IGNORECASE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def redact_value(key: str, value):
    if value is None:
        return None
    if isinstance(value, bytes):
        return "<binary-redacted>"
    if SENSITIVE_KEY_RE.search(key):
        return "***"
    if isinstance(value, str):
        value = EMAIL_RE.sub(lambda match: f"{match.group(1)}***{match.group(3)}", value)
        value = SECRET_VALUE_RE.sub("***", value)
    return value


def export_sqlite_config(db_path: Path) -> dict:
    exported: dict = {"sqlite_path": str(db_path), "tables": {}, "skipped_tables": []}
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        table_names = [
            row["name"]
            for row in conn.execute(
                "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"
            )
        ]
        for table_name in table_names:
            count = conn.execute(f'select count(*) as count from "{table_name}"').fetchone()["count"]
            if SKIP_TABLE_RE.search(table_name) or not EXPORT_TABLE_RE.search(table_name):
                exported["skipped_tables"].append({"name": table_name, "row_count": count})
                continue

            columns = [row["name"] for row in conn.execute(f'pragma table_info("{table_name}")')]
            rows = []
            for row in conn.execute(f'select * from "{table_name}" order by rowid'):
                rows.append({column: redact_value(column, row[column]) for column in columns})
            exported["tables"][table_name] = {"row_count": count, "rows": rows}
    return exported


def prune_old_exports(output_dir: Path, retention_days: int) -> None:
    cutoff = utc_now().timestamp() - retention_days * 86400
    for path in output_dir.glob("one-api-config-*.json*"):
        if path.stat().st_mtime < cutoff:
            path.unlink()


def main() -> None:
    output_dir = Path(os.getenv("ONE_API_CONFIG_BACKUP_DIR", "./backups/one-api"))
    retention_days = int(os.getenv("ONE_API_CONFIG_RETENTION_DAYS", "90"))
    sqlite_path = Path(os.getenv("ONE_API_SQLITE_DB", "/data/one-api.db"))
    output_dir.mkdir(parents=True, exist_ok=True)

    exported_at = utc_now().strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "exported_at_utc": exported_at,
        "retention_days": retention_days,
        "source": "one-api",
        "redaction": "secret-like column names, bearer tokens, sk-* keys, emails, and binary values are redacted",
        "environment": {
            "ONE_API_SQL_DSN_SET": bool(os.getenv("ONE_API_SQL_DSN")),
            "LLM_GATEWAY_ENABLED": os.getenv("LLM_GATEWAY_ENABLED"),
            "LLM_GATEWAY_BASE_URL": os.getenv("LLM_GATEWAY_BASE_URL"),
            "LLM_GATEWAY_MODEL_NAME": os.getenv("LLM_GATEWAY_MODEL_NAME"),
            "LLM_GATEWAY_API_KEY_SET": bool(os.getenv("LLM_GATEWAY_API_KEY")),
        },
    }

    if sqlite_path.exists():
        payload["status"] = "ok"
        payload["config"] = export_sqlite_config(sqlite_path)
    else:
        payload["status"] = "sqlite_db_not_found"
        payload["config"] = {
            "message": "Set ONE_API_SQLITE_DB or ONE_API_SQL_DSN export process before relying on this backup."
        }

    output_file = output_dir / f"one-api-config-{exported_at}.json"
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    output_file.write_text(data + "\n", encoding="utf-8")
    digest = hashlib.sha256(output_file.read_bytes()).hexdigest()
    output_file.with_suffix(output_file.suffix + ".sha256").write_text(
        f"{digest}  {output_file.name}\n",
        encoding="utf-8",
    )
    prune_old_exports(output_dir, retention_days)
    print(f"one-api config export created: {output_file}")


if __name__ == "__main__":
    main()
