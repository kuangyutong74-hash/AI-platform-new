"""重建仅用于开发的 Core 测试数据；不会触碰模块内部数据库或 .env。"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "ai_bole_core_v1.db"
SNAPSHOT_DIR = DATA_DIR / "v1-snapshots"


def backup(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as destination:
        origin.backup(destination)


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="备份并重建 AI 伯乐 Core 开发测试数据")
    parser.add_argument("--confirm", action="store_true", help="确认清空 Core 账号、证据、作品、报告和快照")
    args = parser.parse_args()
    if not args.confirm:
        parser.error("这是破坏性操作；请显式传入 --confirm")
    if DATA_DIR.resolve().parent != ROOT.resolve():
        raise RuntimeError("拒绝操作非平台 Core 数据目录")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = DATA_DIR / "backups" / f"v0-test-reset-{timestamp}"
    if DB_PATH.exists():
        backup(DB_PATH, backup_dir / DB_PATH.name)
    if SNAPSHOT_DIR.exists():
        shutil.copytree(SNAPSHOT_DIR, backup_dir / SNAPSHOT_DIR.name, dirs_exist_ok=True)
    for path in (DB_PATH, Path(f"{DB_PATH}-wal"), Path(f"{DB_PATH}-shm")):
        if path.exists(): path.unlink()
    if SNAPSHOT_DIR.exists(): shutil.rmtree(SNAPSHOT_DIR)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    import main
    main.initialize_database()
    with main.connect() as db:
        tables = [row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    if "evidence_events" in tables:
        raise RuntimeError("重建失败：仍检测到 V0 evidence_events")
    print(f"已重建纯 V1 Core 数据库；备份位置：{backup_dir}")
    print("表：" + ", ".join(tables))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
