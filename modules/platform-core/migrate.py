"""V1-only Core 数据库校验工具。

历史 V0 数据不再迁移；检测到旧表时请运行 reset_dev_data.py --confirm。
"""
from __future__ import annotations

import argparse
import json

import main


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="校验 AI 伯乐纯 V1 Core 数据库")
    parser.add_argument("--dry-run", action="store_true", help="兼容旧命令；仅执行只读校验")
    parser.parse_args()
    with main.connect() as db:
        tables = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        foreign_keys = [dict(row) for row in db.execute("PRAGMA foreign_key_check")]
        result = {"v1Only": "evidence_events" not in tables, "foreignKeyErrors": foreign_keys, "tables": sorted(tables)}
    if not result["v1Only"]:
        raise RuntimeError("检测到 V0 数据表；请运行 reset_dev_data.py --confirm")
    if foreign_keys:
        raise RuntimeError("V1 数据库外键校验失败")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
