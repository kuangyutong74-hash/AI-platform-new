"""AI 伯乐 Core 数据迁移工具。

示例：
  python migrate.py --dry-run
  python migrate.py

dry-run 会先用 SQLite Online Backup API 复制数据库，并只在临时副本上回填和核验。
正式执行会在 data/backups 下留下执行前备份，再应用尚未记录的迁移。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import main


def online_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as destination_db:
        source_db.backup(destination_db)


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="执行 AI 伯乐 Core 的可重复数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅在临时副本上执行，不修改正式数据库")
    args = parser.parse_args()

    source_db = main.DB_PATH
    if args.dry_run:
        temp_dir = Path(tempfile.mkdtemp(prefix="ai-bole-migration-"))
        target_db = temp_dir / source_db.name
        online_backup(source_db, target_db)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = source_db.parent / "backups" / f"{source_db.stem}-{timestamp}.db"
        online_backup(source_db, backup)
        target_db = source_db

    original_db = main.DB_PATH
    main.DB_PATH = target_db
    try:
        main.initialize_database()
        with main.connect() as db:
            result = main.apply_pending_data_migrations(db, source="platform-core.migrate.py")
        print(json.dumps({"dryRun": args.dry_run, "database": str(target_db), "result": result}, ensure_ascii=False, indent=2))
    finally:
        main.DB_PATH = original_db
        if args.dry_run:
            shutil.rmtree(target_db.parent, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
