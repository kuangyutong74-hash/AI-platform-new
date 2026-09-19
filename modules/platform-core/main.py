"""AI伯乐平台核心服务：统一账号与最小化行为证据仓库。

设计原则：
1. 四个模块只提交可解释、可回溯的证据事件，不上传无关点击流。
2. 证据不直接换算分数，只保留强正向/参考证据和原始上下文。
3. 统一账号通过 localhost 下的 HttpOnly Cookie 在不同端口间共享。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import base64
import os
import re
import secrets
import sqlite3
import uuid
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import Cookie, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from jsonschema import Draft202012Validator, FormatChecker

from reports import ANALYSIS_VERSION, DEEP_SEA_SESSION_EVENT, generate_internal_report


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
MODULE_CONFIG_DIR = REPO_ROOT / "config" / "modules"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR = DATA_DIR / "v1-snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("AI_BOLE_DB_PATH", DATA_DIR / "ai_bole_core_v1.db")).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
COOKIE_NAME = "ai_bole_session"
SESSION_DAYS = 30

MODULES = {"chat", "story", "deep_sea", "career"}
CANONICAL_INTELLIGENCES = {
    "linguistic", "logical", "spatial",
    "interpersonal", "intrapersonal", "naturalistic",
}
INTELLIGENCE_NAMES = {
    "linguistic": "语言智能",
    "logical": "逻辑—数学智能",
    "spatial": "空间智能",
    "interpersonal": "人际智能",
    "intrapersonal": "内省智能",
    "naturalistic": "自然观察智能",
}

app = FastAPI(title="AI伯乐平台核心服务", version="1.0.0")
logger = logging.getLogger("ai_bole.core")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173", "http://localhost:3000", "http://localhost:5174",
        "http://localhost:3001", "http://localhost:8000", "http://localhost:5175",
    ],
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    db.execute("PRAGMA journal_mode = WAL")
    return db


@lru_cache(maxsize=32)
def load_json_schema(relative_path: str) -> Draft202012Validator:
    try:
        schema = json.loads((REPO_ROOT / "packages" / "contracts" / "schemas" / relative_path).read_text(encoding="utf-8"))
        return Draft202012Validator(schema, format_checker=FormatChecker())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"契约文件无效：{relative_path}") from exc


def validate_schema(relative_path: str, value: dict, message: str) -> None:
    errors = sorted(load_json_schema(relative_path).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise HTTPException(422, f"{message}：{errors[0].message}")


def load_module_catalog() -> list[dict]:
    """读取版本化模块清单；Portal 只消费该目录，不再维护第二份固定 URL。"""
    catalog: list[dict] = []
    for path in sorted(MODULE_CONFIG_DIR.glob("*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"模块清单无效：{path.name}") from exc
        validate_schema("module-manifest.v1.schema.json", manifest, f"模块清单无效：{path.name}")
        if manifest["id"] not in MODULES: raise RuntimeError(f"未知模块清单：{path.name}")
        catalog.append(manifest)
    if {item["id"] for item in catalog} != MODULES:
        raise RuntimeError("模块清单必须完整登记 chat、story、deep_sea、career")
    # 清单文件名仅用于版本管理，不能决定首页四个入口的产品顺序。
    order = {module_id: index for index, module_id in enumerate(("chat", "story", "deep_sea", "career"))}
    return sorted(catalog, key=lambda item: order[item["id"]])


def initialize_database() -> None:
    with connect() as db:
        legacy = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='evidence_events'").fetchone()
        if legacy:
            raise RuntimeError("检测到已废弃的 V0 测试数据库；请停止服务后运行 reset_dev_data.py --confirm")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL,
              age INTEGER NOT NULL,
              password_hash TEXT NOT NULL,
              password_salt TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS account_sessions (
              id TEXT PRIMARY KEY,
              account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON account_sessions(token_hash);
            CREATE TABLE IF NOT EXISTS child_profiles (
              id TEXT PRIMARY KEY,
              account_id TEXT NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
              display_name TEXT NOT NULL,
              age INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'runtime',
              result_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS modules (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              current_version TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS module_versions (
              module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
              version TEXT NOT NULL,
              contract_version TEXT NOT NULL,
              construct_registry_version TEXT NOT NULL,
              manifest_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (module_id, version)
            );
            CREATE TABLE IF NOT EXISTS assessment_sessions (
              id TEXT PRIMARY KEY,
              child_profile_id TEXT NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
              module_id TEXT NOT NULL,
              module_version TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('created','active','interrupted','completed','abandoned')),
              created_at TEXT NOT NULL,
              started_at TEXT,
              ended_at TEXT,
              active_seconds INTEGER NOT NULL DEFAULT 0,
              state_version INTEGER NOT NULL DEFAULT 1,
              summary_json TEXT NOT NULL DEFAULT '{}',
              interruption_reason TEXT,
              FOREIGN KEY (module_id, module_version) REFERENCES module_versions(module_id, version)
            );
            CREATE TABLE IF NOT EXISTS module_authorizations (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
              launch_code_hash TEXT NOT NULL UNIQUE,
              launch_expires_at TEXT NOT NULL,
              exchanged_at TEXT,
              token_hash TEXT UNIQUE,
              scopes_json TEXT NOT NULL,
              expires_at TEXT,
              revoked_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS source_events (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
              idempotency_key TEXT NOT NULL,
              event_type TEXT NOT NULL,
              schema_version TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              sequence_no INTEGER,
              occurred_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(session_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS evidence_records (
              id TEXT PRIMARY KEY,
              source_event_id TEXT NOT NULL REFERENCES source_events(id) ON DELETE CASCADE,
              evidence_level TEXT NOT NULL CHECK(evidence_level IN ('strong','reference')),
              constructs_json TEXT NOT NULL,
              behavior_summary TEXT NOT NULL,
              policy_version TEXT NOT NULL,
              construct_registry_version TEXT NOT NULL,
              derived_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
              type TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              preview_resource_id TEXT,
              source_resource_id TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshot_assets (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES assessment_sessions(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
              id TEXT PRIMARY KEY,
              child_profile_id TEXT NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
              generator_version TEXT NOT NULL,
              ruleset_version TEXT NOT NULL,
              prompt_version TEXT,
              model_id TEXT,
              evidence_set_hash TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('draft','published','failed')),
              report_json TEXT NOT NULL,
              generated_at TEXT NOT NULL,
              published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS report_evidence_links (
              report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
              evidence_record_id TEXT NOT NULL REFERENCES evidence_records(id) ON DELETE RESTRICT,
              section_key TEXT NOT NULL,
              PRIMARY KEY (report_id, evidence_record_id, section_key)
            );
            CREATE TABLE IF NOT EXISTS parent_feedback (
              id TEXT PRIMARY KEY,
              report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
              child_profile_id TEXT NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
              author_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              dimension_key TEXT NOT NULL,
              questions_json TEXT NOT NULL,
              answers_json TEXT NOT NULL,
              suggestion_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(report_id, author_account_id, dimension_key)
            );
            CREATE TABLE IF NOT EXISTS adult_student_links (
              adult_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              student_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL,
              PRIMARY KEY (adult_account_id, student_account_id)
            );
            CREATE TABLE IF NOT EXISTS work_comments (
              id TEXT PRIMARY KEY,
              student_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              work_id TEXT NOT NULL,
              author_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              body TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS manual_works (
              id TEXT PRIMARY KEY,
              student_account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              module TEXT NOT NULL,
              work_type TEXT NOT NULL DEFAULT '',
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              source_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_adult_links_student ON adult_student_links(student_account_id);
            CREATE INDEX IF NOT EXISTS idx_work_comments_student_work ON work_comments(student_account_id, work_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_manual_works_student_time ON manual_works(student_account_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_assessment_profile_time ON assessment_sessions(child_profile_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_source_event_session_time ON source_events(session_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_snapshot_session ON snapshot_assets(session_id);
            CREATE INDEX IF NOT EXISTS idx_parent_feedback_child ON parent_feedback(child_profile_id, created_at DESC);
            """
        )
        account_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(accounts)").fetchall()
        }
        for column, definition in (
            ("role", "TEXT NOT NULL DEFAULT 'student'"),
            ("adult_kind", "TEXT"),
            ("recovery_hash", "TEXT"),
            ("recovery_salt", "TEXT"),
            ("avatar_id", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in account_columns:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {column} {definition}")
        session_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(account_sessions)").fetchall()
        }
        if "selected_student_id" not in session_columns:
            db.execute("ALTER TABLE account_sessions ADD COLUMN selected_student_id TEXT")
        assessment_columns = {row["name"] for row in db.execute("PRAGMA table_info(assessment_sessions)").fetchall()}
        if "summary_json" not in assessment_columns:
            db.execute("ALTER TABLE assessment_sessions ADD COLUMN summary_json TEXT NOT NULL DEFAULT '{}'")
        if "interruption_reason" not in assessment_columns:
            db.execute("ALTER TABLE assessment_sessions ADD COLUMN interruption_reason TEXT")
        manual_work_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(manual_works)").fetchall()
        }
        if "source_id" not in manual_work_columns:
            db.execute("ALTER TABLE manual_works ADD COLUMN source_id TEXT NOT NULL DEFAULT ''")
        if "work_type" not in manual_work_columns:
            db.execute("ALTER TABLE manual_works ADD COLUMN work_type TEXT NOT NULL DEFAULT ''")
        db.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_manual_works_student_source
               ON manual_works(student_account_id, module, source_id)
               WHERE source_id <> ''"""
        )
        migration_columns = {row["name"] for row in db.execute("PRAGMA table_info(schema_migrations)").fetchall()}
        if "source" not in migration_columns:
            db.execute("ALTER TABLE schema_migrations ADD COLUMN source TEXT NOT NULL DEFAULT 'runtime'")
        if "result_json" not in migration_columns:
            db.execute("ALTER TABLE schema_migrations ADD COLUMN result_json TEXT NOT NULL DEFAULT '{}'")
        timestamp = datetime.now(timezone.utc).isoformat()
        db.execute(
            """INSERT OR IGNORE INTO schema_migrations (version,applied_at,source,result_json)
               VALUES (?,?,?,?)""",
            ("20260829_v1_only_baseline", timestamp, "platform-core.initialize_database", "{}"),
        )
        db.execute(
            """INSERT OR IGNORE INTO child_profiles (id,account_id,display_name,age,created_at,updated_at)
               SELECT id,id,display_name,age,created_at,updated_at FROM accounts
               WHERE COALESCE(role,'student')='student'"""
        )
        ensure_default_test_accounts(db, timestamp)
        for manifest in load_module_catalog():
            db.execute(
                """INSERT INTO modules (id,name,enabled,current_version,updated_at) VALUES (?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, current_version=excluded.current_version, updated_at=excluded.updated_at""",
                (manifest["id"], manifest["name"], 1, manifest["version"], timestamp),
            )
            db.execute(
                """INSERT OR IGNORE INTO module_versions
                   (module_id,version,contract_version,construct_registry_version,manifest_json,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (manifest["id"], manifest["version"], "1.0", manifest["constructRegistryVersion"], json.dumps(manifest, ensure_ascii=False), timestamp),
            )
        db.execute("PRAGMA optimize")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def password_digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 180_000).hex()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def canonical_generated_username(value: str) -> str:
    """容错自动账号的常见抄写形式，例如 S2026001 或 S2026-0001。"""
    match = re.fullmatch(r"([sa])(\d{4})-?(\d{1,4})", value)
    if not match:
        return value
    role, year, sequence = match.groups()
    return f"{role}{year}{sequence.zfill(4)}"


def find_account_by_username(db: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    """精确账号优先；不存在时再兼容自动账号漏写前导零的输入。"""
    account = db.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
    if account:
        return account
    canonical = canonical_generated_username(username)
    if canonical == username:
        return None
    return db.execute("SELECT * FROM accounts WHERE username=?", (canonical,)).fetchone()


def ensure_default_test_accounts(db: sqlite3.Connection, timestamp: str) -> None:
    """为本地实验环境提供稳定、可重复登录的学生与成人测试账号。"""
    if os.environ.get("AI_BOLE_SEED_TEST_ACCOUNTS", "1").strip().lower() in {"0", "false", "no", "off"}:
        return

    password = os.environ.get("AI_BOLE_TEST_ACCOUNT_PASSWORD", "demo1234")

    def ensure_account(username: str, display_name: str, age: int, role: str) -> sqlite3.Row:
        existing = db.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
        if existing:
            return existing
        account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-bole.local/{username}"))
        salt = secrets.token_hex(16)
        db.execute(
            """INSERT INTO accounts
               (id,username,display_name,age,password_hash,password_salt,created_at,updated_at,role,adult_kind)
               VALUES (?,?,?,?,?,?,?,?,?,NULL)""",
            (account_id, username, display_name, age, password_digest(password, salt), salt,
             timestamp, timestamp, role),
        )
        return db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()

    student = ensure_account("student_demo", "测试学生小星", 9, "student")
    adult = ensure_account("adult_demo", "测试家长", 0, "adult")
    if (student["role"] or "student") != "student" or (adult["role"] or "student") != "adult":
        logger.warning("默认测试账号名称已被其他角色占用，跳过自动绑定")
        return

    db.execute(
        """INSERT OR IGNORE INTO child_profiles
           (id,account_id,display_name,age,created_at,updated_at) VALUES (?,?,?,?,?,?)""",
        (student["id"], student["id"], student["display_name"], student["age"], timestamp, timestamp),
    )
    db.execute(
        "INSERT OR IGNORE INTO adult_student_links (adult_account_id,student_account_id,created_at) VALUES (?,?,?)",
        (adult["id"], student["id"], timestamp),
    )
    samples = (
        ("demo-work-story", "story", "星星邮差", "我设计了一个把勇气送到每颗星球的故事。"),
        ("demo-work-deep-sea", "deep_sea", "会发光的海底基地", "我调整了基地布局，让小鱼和珊瑚都有安全空间。"),
    )
    for work_id, module, title, description in samples:
        db.execute(
            """INSERT OR IGNORE INTO manual_works
               (id,student_account_id,module,title,description,created_at) VALUES (?,?,?,?,?,?)""",
            (work_id, student["id"], module, title, description, timestamp),
        )


def public_account(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "age": row["age"],
        "created_at": row["created_at"],
        "role": row["role"] or "student",
        "adult_kind": row["adult_kind"],
        "avatar_id": row["avatar_id"] or None,
    }


def require_account(token: str | None) -> sqlite3.Row:
    if not token:
        raise HTTPException(401, "尚未登录统一账号")
    with connect() as db:
        row = db.execute(
            """SELECT a.* FROM account_sessions s JOIN accounts a ON a.id=s.account_id
               WHERE s.token_hash=? AND s.expires_at>?""",
            (token_digest(token), now_iso()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "登录状态已失效")
    return row


def linked_students(db: sqlite3.Connection, adult_id: str) -> list[sqlite3.Row]:
    return db.execute(
        """SELECT s.* FROM adult_student_links l
           JOIN accounts s ON s.id=l.student_account_id
           WHERE l.adult_account_id=? ORDER BY l.created_at, s.username""",
        (adult_id,),
    ).fetchall()


def resolve_subject(viewer: sqlite3.Row, token: str | None) -> sqlite3.Row:
    """学生读取自己；成人只能读取已绑定且当前选中的学生。"""
    if (viewer["role"] or "student") == "student":
        return viewer
    with connect() as db:
        session = db.execute(
            "SELECT selected_student_id FROM account_sessions WHERE token_hash=? AND expires_at>?",
            (token_digest(token or ""), now_iso()),
        ).fetchone()
        students = linked_students(db, viewer["id"])
        if not students:
            raise HTTPException(409, "请先绑定至少一位学生")
        selected_id = session["selected_student_id"] if session else None
        return next((student for student in students if student["id"] == selected_id), students[0])


def require_student_viewer(token: str | None) -> sqlite3.Row:
    account = require_account(token)
    if (account["role"] or "student") != "student":
        raise HTTPException(403, "老师/家长账号不能进入学生探索模块")
    return account


@lru_cache(maxsize=1)
def construct_dimension_map() -> dict[str, str]:
    registry = json.loads((REPO_ROOT / "config" / "construct-registry.v1.json").read_text(encoding="utf-8"))
    return {item["key"]: item["reportDimension"] for item in registry["constructs"]}


@lru_cache(maxsize=1)
def construct_display_name_map() -> dict[str, str]:
    registry = json.loads((REPO_ROOT / "config" / "construct-registry.v1.json").read_text(encoding="utf-8"))
    return {item["key"]: item["displayName"] for item in registry["constructs"]}


def evidence_report_dimensions(row: sqlite3.Row, dimensions: dict[str, str]) -> list[str]:
    """Map standard constructs to report dimensions, including level-specific game evidence."""
    try:
        constructs = json.loads(row["constructs_json"])
    except (TypeError, json.JSONDecodeError):
        constructs = []
    normalized = list(dict.fromkeys(dimensions[item] for item in constructs if item in dimensions))
    if row["module_id"] == "deep_sea" and row["event_type"] == "deep-sea.spatial-task-completed.v1":
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if int(payload.get("level", 0)) == 1 and "naturalistic" not in normalized:
            normalized.append("naturalistic")
        if int(payload.get("level", 0)) == 3:
            # 第三关观察的是协商表达和方案选择，不把同一个完成事件重复
            # 解释为空间搭建或逻辑解谜证据。
            normalized = [item for item in normalized if item not in {"spatial", "logical"}]
            for dimension in ("interpersonal", "linguistic"):
                if dimension not in normalized:
                    normalized.append(dimension)
    return normalized


TREASURE_DIMENSIONS_BY_MODULE = {
    "story": {"linguistic"},
    "deep_sea": {"logical", "spatial", "naturalistic"},
    "chat": {"interpersonal"},
    "career": {"intrapersonal"},
}


def treasure_dimensions_for_event(event: dict) -> set[str]:
    """按实际玩法环节分配藏宝图星星，避免不同星星复述同一段内容。"""
    module = str(event.get("module", ""))
    if module != "deep_sea":
        return set(TREASURE_DIMENSIONS_BY_MODULE.get(module, set()))
    if event.get("event_type") != "deep-sea.spatial-task-completed.v1":
        return set()
    raw = event.get("raw_evidence", {}) if isinstance(event.get("raw_evidence"), dict) else {}
    level = int(raw.get("level", 0) or 0)
    if level == 1:
        return {"naturalistic", "logical"}
    if level == 2:
        return {"spatial", "logical"}
    if level == 3:
        return {"interpersonal"}
    return set()


def build_talent_eligibility(rows: list[sqlite3.Row], completed_modules: set[str] | None = None) -> list[dict]:
    """从标准证据与完整体验推导六星资格。"""
    completed_modules = completed_modules or set()
    aggregates = {
        key: {"strong": 0, "reference": 0, "modules": set(), "completed_modules": set(), "recent_id": None, "recent_module_id": None}
        for key in CANONICAL_INTELLIGENCES
    }
    dimensions = construct_dimension_map()
    for row in rows:
        normalized = set(evidence_report_dimensions(row, dimensions))
        for key in normalized:
            item = aggregates[key]
            item["modules"].add(row["module_id"])
            if item["recent_id"] is None:
                item["recent_id"] = row["id"]
                item["recent_module_id"] = row["module_id"]
            if row["evidence_level"] == "strong":
                item["strong"] += 1
            else:
                item["reference"] += 1
    for module_id in completed_modules:
        for key in TREASURE_DIMENSIONS_BY_MODULE.get(module_id, set()):
            aggregates[key]["modules"].add(module_id)
            aggregates[key]["completed_modules"].add(module_id)
    return [
        {
            "key": key,
            "name": INTELLIGENCE_NAMES[key],
            "strongCount": values["strong"],
            "referenceCount": values["reference"],
            "eligible": bool(values["completed_modules"]),
            "sourceModules": sorted(values["modules"]),
            "completedModules": sorted(values["completed_modules"]),
            "recentEvidenceRecordId": values["recent_id"],
            "recentEvidenceModuleId": values["recent_module_id"],
        }
        for key, values in sorted(aggregates.items())
    ]


def normalize_username(value: str) -> str:
    value = value.strip().lower()
    if not all(ch.isalnum() or ch in "_-" for ch in value):
        raise ValueError("账号只能包含文字、数字、下划线或短横线")
    return value


class AccountCredentialsIn(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    # 兼容旧版本已创建的 4～5 位密码；新注册仍要求至少 6 位。
    password: str = Field(min_length=4, max_length=72)
    expected_role: Literal["student", "adult"] | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return normalize_username(value)


class AccountRegistrationIn(BaseModel):
    username: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(min_length=1, max_length=30)
    age: int | None = None
    role: Literal["student", "adult"] = "student"
    adult_kind: Literal["parent", "teacher"] | None = None

    @field_validator("username")
    @classmethod
    def normalize_optional_username(cls, value: str | None) -> str | None:
        return normalize_username(value) if value and value.strip() else None

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写昵称")
        return value

    @model_validator(mode="after")
    def validate_role_fields(self):
        if self.role == "student":
            if self.age is None or not 4 <= self.age <= 18:
                raise ValueError("学生年龄需填写 4～18 岁")
            self.adult_kind = None
        else:
            # 测试阶段统一使用成人端，不区分家长与老师。
            self.adult_kind = None
        return self


class PasswordResetIn(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    new_password: str = Field(min_length=6, max_length=72)

    @field_validator("username")
    @classmethod
    def normalize_reset_username(cls, value: str) -> str:
        return normalize_username(value)


class StudentLinkIn(BaseModel):
    username: str = Field(min_length=2, max_length=30)

    @field_validator("username")
    @classmethod
    def normalize_student_username(cls, value: str) -> str:
        return normalize_username(value)


class StudentContextIn(BaseModel):
    student_id: str = Field(min_length=1, max_length=80)


class StudentIdentityIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=30)
    avatar_id: Literal["student-1", "student-2", "student-3", "student-4", "student-5", "student-6"]

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写昵称")
        return value


class WorkCommentIn(BaseModel):
    work_id: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=300)

    @field_validator("body")
    @classmethod
    def normalize_comment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请写下点评内容")
        return value


class ManualWorkIn(BaseModel):
    module: Literal["story", "deep_sea", "career", "chat"]
    work_type: str = Field(default="", max_length=40)
    title: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=20000)
    source_id: str = Field(default="", max_length=160)

    @field_validator("title")
    @classmethod
    def normalize_manual_work_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写作品名称")
        return value

    @field_validator("description")
    @classmethod
    def normalize_manual_work_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_id")
    @classmethod
    def normalize_manual_work_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("work_type")
    @classmethod
    def normalize_manual_work_type(cls, value: str) -> str:
        return value.strip()


class DeprecatedEvidenceIn(BaseModel):
    """仅用于让已移除路由在开发中保持 404；不再连接任何数据表。"""
    module: str
    event_type: str
    occurred_at: str = Field(default_factory=now_iso)
    evidence_level: Literal["strong", "reference"]
    intelligence_candidates: list[str] = Field(default_factory=list)
    behavior_summary: str
    raw_evidence: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)


class AssessmentSessionIn(BaseModel):
    module_id: str = Field(min_length=2, max_length=64)


class LaunchCodeExchangeIn(BaseModel):
    launch_code: str = Field(alias="launchCode", min_length=20, max_length=256)
    model_config = ConfigDict(populate_by_name=True)


class EvidenceEnvelopeIn(BaseModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    event_id: str = Field(alias="eventId", min_length=1, max_length=128)
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=160)
    event_type: str = Field(alias="eventType", min_length=3, max_length=120)
    occurred_at: str = Field(alias="occurredAt", min_length=10, max_length=64)
    sequence_no: int | None = Field(default=None, alias="sequenceNo", ge=0)
    payload: dict
    model_config = ConfigDict(populate_by_name=True)


class EvidenceBatchIn(BaseModel):
    events: list[EvidenceEnvelopeIn] = Field(min_length=1, max_length=100)


class ParentFeedbackIn(BaseModel):
    dimension_key: str = Field(min_length=2, max_length=64)
    questions: list[dict] = Field(default_factory=list, max_length=8)
    answers: list[dict] = Field(default_factory=list, max_length=8)


class SessionStatusIn(BaseModel):
    status: Literal["completed", "interrupted", "abandoned", "active"]
    state_version: int | None = Field(default=None, alias="stateVersion", ge=1)
    summary: dict = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=240)
    model_config = ConfigDict(populate_by_name=True)


class ArtifactIn(BaseModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    artifact_id: str = Field(alias="artifactId", min_length=1, max_length=128)
    type: Literal["story", "snapshot", "conversation", "game-result", "other"]
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(max_length=500)
    preview_resource_id: str | None = Field(default=None, alias="previewResourceId")
    source_resource_id: str | None = Field(default=None, alias="sourceResourceId")
    created_at: str = Field(alias="createdAt")
    model_config = ConfigDict(populate_by_name=True)


def module_manifest(module_id: str) -> dict:
    for manifest in load_module_catalog():
        if manifest["id"] == module_id:
            return manifest
    raise HTTPException(404, "体验模块不存在")


def profile_for_account(db: sqlite3.Connection, account_id: str) -> sqlite3.Row:
    profile = db.execute("SELECT * FROM child_profiles WHERE account_id=?", (account_id,)).fetchone()
    if not profile:
        raise HTTPException(409, "儿童档案尚未完成迁移")
    return profile


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "缺少模块授权")
    return authorization[7:].strip()


def require_module_authorization(authorization: str | None) -> sqlite3.Row:
    token = bearer_token(authorization)
    with connect() as db:
        authorization_row = db.execute(
            """SELECT a.*, s.status, s.module_id, s.module_version, s.child_profile_id
               FROM module_authorizations a JOIN assessment_sessions s ON s.id=a.session_id
               WHERE a.token_hash=? AND a.expires_at>? AND a.revoked_at=''""",
            (token_digest(token), now_iso()),
        ).fetchone()
    if not authorization_row:
        raise HTTPException(401, "模块授权已失效")
    return authorization_row


def validate_evidence_event(event: EvidenceEnvelopeIn) -> None:
    validate_schema("evidence/envelope.v1.schema.json", event.model_dump(by_alias=True, exclude_none=True), "证据 Envelope 无效")
    validate_schema(f"evidence/{event.event_type}.schema.json", event.payload, "证据 Payload 无效")


def policy_for_event(event_type: str) -> dict:
    policy_path = REPO_ROOT / "config" / "evidence-policy.v1.json"
    try: policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise HTTPException(503, "证据策略暂不可用") from exc
    rule = next((item for item in policy["rules"] if item["eventType"] == event_type), None)
    if not rule:
        raise HTTPException(422, "该事件未配置证据策略")
    return {**rule, "policyVersion": policy["version"], "constructRegistryVersion": policy["constructRegistryVersion"]}


initialize_database()

CAREER_DB_PATH = REPO_ROOT / "modules" / "career" / "backend" / "career_sim.db"
STORY_DB_PATH = REPO_ROOT / "modules" / "story" / "story_cocreate.db"


def career_mentor_reflections(db: sqlite3.Connection, profile_id: str, career_id: str, occurred_at: str) -> list[dict[str, str]]:
    """关联同一孩子、同一职业且时间最接近的导师对话；严格按平台账号 id 匹配，绝不按名字猜测。

    child_profiles.id 与 accounts.id 同源，career 后端在创建会话时把平台账号 id 写入
    sessions.student_token；此处以 student_token 作为唯一归属键，避免重名孩子互相串户。
    """
    if not profile_id or not career_id or not CAREER_DB_PATH.exists():
        return []
    try:
        target = datetime.fromisoformat(occurred_at.replace("Z", "+00:00")).replace(tzinfo=None)
        with sqlite3.connect(CAREER_DB_PATH) as career_db:
            career_db.row_factory = sqlite3.Row
            sessions = career_db.execute(
                "SELECT id,created_at FROM sessions WHERE student_token=? AND career_id=? ORDER BY created_at DESC LIMIT 12",
                (profile_id, career_id),
            ).fetchall()
            if not sessions:
                return []
            ranked = []
            for session in sessions:
                try: distance = abs((datetime.fromisoformat(str(session["created_at"])).replace(tzinfo=None) - target).total_seconds())
                except ValueError: continue
                if distance <= 3 * 86400: ranked.append((distance, session["id"]))
            if not ranked:
                return []
            session_id = min(ranked)[1]
            rows = career_db.execute(
                """SELECT sr.scenario_title,fu.ai_question,fu.student_answer
                   FROM scenario_records sr JOIN choice_records cr ON cr.scenario_record_id=sr.id
                   JOIN follow_up_records fu ON fu.choice_record_id=cr.id
                   WHERE sr.session_id=? AND length(trim(coalesce(fu.student_answer,'')))>0
                   ORDER BY sr.scenario_index,fu.created_at""", (session_id,),
            ).fetchall()
        return [{"scenarioTitle": str(item["scenario_title"] or "").strip(), "question": str(item["ai_question"] or "").strip(), "answer": str(item["student_answer"] or "").strip()[:500]} for item in rows]
    except (sqlite3.Error, OSError):
        logger.warning("无法读取职业导师对话", exc_info=True)
        return []


def sync_collected_story_evidence(db: sqlite3.Connection, profile_id: str) -> None:
    """Turn stories collected from the co-creation module into reportable evidence.

    The gallery's “add to my works” path predates the module SDK, so those stories
    were visible in My Works but had no evidence row for the magic book.
    """
    works = db.execute(
        """SELECT mw.* FROM manual_works mw
           JOIN child_profiles cp ON cp.account_id=mw.student_account_id
           WHERE cp.id=? AND mw.module='story' AND mw.source_id LIKE 'story:%'""",
        (profile_id,),
    ).fetchall()
    if not works:
        return
    manifest = module_manifest("story")
    policy = policy_for_event("story.contribution-completed.v1")
    for work in works:
        session_id = f"collected-story:{work['id']}"
        event_id = f"collected-story-event:{work['id']}"
        evidence_id = f"collected-story-evidence:{work['id']}"
        summary = {
            "storyTitle": work["title"],
            "storySynopsis": str(work["description"] or "")[:260],
            "collectedFromStoryModule": True,
            "manualWorkId": work["id"],
        }
        db.execute(
            """INSERT INTO assessment_sessions
               (id,child_profile_id,module_id,module_version,status,created_at,started_at,ended_at,active_seconds,state_version,summary_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET summary_json=excluded.summary_json,ended_at=excluded.ended_at""",
            (session_id, profile_id, "story", manifest["version"], "completed", work["created_at"], work["created_at"], work["created_at"], 0, 1, json.dumps(summary, ensure_ascii=False)),
        )
        event_payload = {"contributionCount": 1, "completionSeconds": 0, "storyTitle": work["title"]}
        db.execute(
            """INSERT INTO source_events
               (id,session_id,idempotency_key,event_type,schema_version,payload_json,sequence_no,occurred_at,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json,occurred_at=excluded.occurred_at""",
            (event_id, session_id, f"collected-story:{work['id']}", "story.contribution-completed.v1", "1.0", json.dumps(event_payload, ensure_ascii=False), 1, work["created_at"], work["created_at"]),
        )
        db.execute(
            """INSERT INTO evidence_records
               (id,source_event_id,evidence_level,constructs_json,behavior_summary,policy_version,construct_registry_version,derived_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET behavior_summary=excluded.behavior_summary,derived_at=excluded.derived_at""",
            (evidence_id, event_id, policy["evidenceLevel"], json.dumps(policy["constructs"], ensure_ascii=False), f"完成故事《{work['title']}》的共创表达", policy["policyVersion"], policy["constructRegistryVersion"], now_iso()),
        )


def standard_events_for_report(db: sqlite3.Connection, profile_id: str) -> tuple[list[dict], list[str]]:
    """将 V1 事件和派生证据投影为报告输入，引用始终使用 evidence record ID。"""
    sync_collected_story_evidence(db, profile_id)
    rows = db.execute(
        """SELECT se.*, er.id AS evidence_id, er.evidence_level, er.constructs_json, er.behavior_summary,
                  s.module_id, s.summary_json
           FROM source_events se JOIN evidence_records er ON er.source_event_id=se.id
           JOIN assessment_sessions s ON s.id=se.session_id
           WHERE s.child_profile_id=? ORDER BY se.occurred_at ASC""", (profile_id,)
    ).fetchall()
    dimension_by_construct = construct_dimension_map()
    # 单关记录写入时整场还没结束，无法判断它是否留下了完整过程。这里按会话
    # 回填“这一场是否走完”，报告侧据此判定卡片是“较完整记录”还是“参考线索”。
    completed_sessions = {row["session_id"] for row in rows if row["event_type"] == DEEP_SEA_SESSION_EVENT}
    events = []
    for row in rows:
        constructs = json.loads(row["constructs_json"])
        payload = json.loads(row["payload_json"])
        # 旧版第一关事件只保存了“关卡已完成”。第一关完成即代表 4 组
        # 生物全部配对成功，可可靠恢复最终准确度；检查次数无法恢复，绝不猜测。
        if row["event_type"] == "deep-sea.spatial-task-completed.v1" and int(payload.get("level", 0)) == 1:
            payload.setdefault("successfulPairs", 4)
            payload.setdefault("totalPairs", 4)
            payload.setdefault("accuracyPercent", 100)
        artifacts = db.execute(
            "SELECT type,title,summary,source_resource_id,created_at FROM artifacts WHERE session_id=? ORDER BY created_at DESC",
            (row["session_id"],),
        ).fetchall()
        context = {"sourceEventId": row["id"], "constructs": constructs, "sessionSummary": json.loads(row["summary_json"] or "{}"), "artifacts": [{"type": item["type"], "title": item["title"], "summary": item["summary"], "sourceResourceId": item["source_resource_id"], "createdAt": item["created_at"]} for item in artifacts]}
        if row["module_id"] == "story" and not context["sessionSummary"].get("storySynopsis"):
            source = next((item["source_resource_id"] for item in artifacts if str(item["source_resource_id"] or "").startswith("story:")), "")
            match = re.fullmatch(r"story:(\d+)", source)
            story_db_path = REPO_ROOT / "modules" / "story" / "story_cocreate.db"
            if match and story_db_path.exists():
                try:
                    with sqlite3.connect(story_db_path) as story_db:
                        story_db.row_factory = sqlite3.Row
                        story = story_db.execute("SELECT title,full_text FROM stories WHERE id=?", (int(match.group(1)),)).fetchone()
                        child_rows = story_db.execute("SELECT content FROM story_messages WHERE story_id=? AND role='child' ORDER BY turn_number,id", (int(match.group(1)),)).fetchall()
                    if story:
                        clean = re.sub(r"【[^】]+】|你觉得接下来会发生什么呢？", " ", story["full_text"] or "")
                        sentences = [part.strip() for part in re.findall(r"[^。！？!?]+[。！？!?]?", re.sub(r"\s+", " ", clean)) if part.strip()]
                        synopsis_parts = sentences if len(sentences) <= 4 else sentences[:2] + sentences[-2:]
                        child_sentences = [part.strip() for item in child_rows for part in re.findall(r"[^。！？!?]+[。！？!?]?", re.sub(r"\s+", " ", item["content"] or "")) if len(part.strip()) >= 12]
                        vivid = [part for part in child_sentences if re.search(r"像|仿佛|轻轻|忽然|闪|光|声音|香气|颜色|笑|眼睛", part)]
                        highlight = max(vivid or child_sentences, key=len, default="")
                        context["sessionSummary"].update({"storyTitle": story["title"] or payload.get("storyTitle", ""), "storySynopsis": "".join(synopsis_parts)[:260], "childHighlight": highlight[:140]})
                except sqlite3.Error:
                    logger.warning("无法从故事库恢复故事 %s 的回顾内容", match.group(1))
        if row["module_id"] == "chat":
            context["fieldSemantics"] = {
                "topicKey": "进入本次聊天时选择的入口主题，不代表每一轮表达的话题",
                "sessionSummary.childWords": "整场会话中孩子表达的汇总摘录，未与 topicKey 建立轮次对应关系",
            }
            if not payload.get("childTurns"):
                # 旧版记录没有逐轮映射。入口主题与汇总摘录同时交给模型会被
                # 错误拼成一句话，因此报告输入只保留可引用的孩子表达。
                payload.pop("topicKey", None)
                context["artifacts"] = [{**item, "title": "聊天记录"} for item in context["artifacts"]]
        if row["module_id"] == "career":
            reflections = career_mentor_reflections(db, profile_id, str(payload.get("taskKey", "")), row["occurred_at"])
            if reflections:
                context["sessionSummary"]["mentorReflections"] = reflections
        intelligence_candidates = list(dict.fromkeys(dimension_by_construct.get(key) for key in constructs if dimension_by_construct.get(key)))
        # 深海基地第一关（生态配对）映射到自然观察智能
        if row["event_type"] == "deep-sea.spatial-task-completed.v1" and int(payload.get("level", 0)) == 1 and "naturalistic" not in intelligence_candidates:
            intelligence_candidates.append("naturalistic")
        if row["event_type"] == "deep-sea.spatial-task-completed.v1" and int(payload.get("level", 0)) == 3:
            intelligence_candidates = [item for item in intelligence_candidates if item not in {"spatial", "logical"}]
            for dimension in ("interpersonal", "linguistic"):
                if dimension not in intelligence_candidates:
                    intelligence_candidates.append(dimension)
        if row["module_id"] == "career" and context["sessionSummary"].get("mentorReflections") and "intrapersonal" not in intelligence_candidates:
            intelligence_candidates.append("intrapersonal")
        events.append({"id": row["evidence_id"], "module": row["module_id"], "event_type": row["event_type"], "occurred_at": row["occurred_at"], "evidence_level": row["evidence_level"], "session_id": row["session_id"], "session_completed": row["session_id"] in completed_sessions, "intelligence_candidates": intelligence_candidates, "behavior_summary": row["behavior_summary"], "raw_evidence": payload, "context": context})
    return events, [row["evidence_id"] for row in rows]


REPORT_MODULE_QUESTION_BANK = {
    "story": {"lead":"聊聊这次故事","question":"孩子平时讲故事时，通常怎样展开想法？","options":["先想人物","先想情节","边讲边想","很少讲故事"],"placeholder":"比如最近讲过的一个故事"},
    "chat": {"lead":"聊聊日常表达","question":"孩子遇到在意的事，通常会怎样告诉您？","options":["主动说出来","问了才会说","边做边说","暂时不想说"],"placeholder":"可以写下当时的一句话"},
    "deep_sea": {"lead":"聊聊动手尝试","question":"碰到需要反复尝试的任务时，孩子通常怎么做？","options":["自己换办法","请人给提示","先停一会儿","容易放弃"],"placeholder":"比如拼搭、解题或做手工"},
    "career": {"lead":"聊聊面对任务","question":"面对一个没做过的新任务，孩子通常怎样开始？","options":["先观察再做","马上动手试","先问清步骤","需要陪着做"],"placeholder":"可以写下最近的一次尝试"},
}
REPORT_QUESTION_VERSION = "module-bank-v1"
# 与报告生成侧共用同一个分析版本。两边写死不同字符串时，缓存校验会一直判定
# “旧报告”，家长端要么拿不到缓存，要么看到上一版文案。
REPORT_ANALYSIS_VERSION = ANALYSIS_VERSION


def fallback_report_questions(child_name: str, report: dict, events: list[dict]) -> dict:
    """Build usable parent questions even when the optional report model is slow."""
    event_by_id = {str(event.get("id")): event for event in events if event.get("id")}
    explanation_by_id = {
        str(item.get("evidence_ref")): item
        for item in report.get("evidence_explanations", [])
        if isinstance(item, dict) and item.get("evidence_ref")
    }
    question_candidates = []
    seen_modules = set()
    for dimension in report.get("dimensions", []):
        refs = dimension.get("evidence_refs", []) if isinstance(dimension, dict) else []
        for evidence_ref in reversed([str(value) for value in refs]):
            event = event_by_id.get(evidence_ref, {})
            module = event.get("module")
            if module not in REPORT_MODULE_QUESTION_BANK or module in seen_modules:
                continue
            explanation = explanation_by_id.get(evidence_ref, {})
            brief = str(explanation.get("summary") or dimension.get("analysis") or "报告中已经留下了一次真实观察")[:72]
            question_candidates.append((list(REPORT_MODULE_QUESTION_BANK).index(module), dimension, evidence_ref, module, brief))
            seen_modules.add(module)
    question_candidates.sort(key=lambda item: item[0])
    dimension_questions = []
    for _, dimension, evidence_ref, module, brief in question_candidates:
        preset = REPORT_MODULE_QUESTION_BANK[module]
        dimension_questions.append({"id":f"d{len(dimension_questions)+1}","key":dimension.get("key"),"evidence_ref":evidence_ref,"module":module,"evidence_brief":brief,**preset,"allow_text":True})
    name = child_name or "孩子"
    return {
        "question_version": REPORT_QUESTION_VERSION,
        "lead_note": f"也想听听您眼中的{name}。这些日常片段会和游戏记录一起写进建议。"[:40],
        "global_questions": [
            {"id":"g1","category":"家庭陪伴","lead":"关于陪伴——","question":f"平时谁陪{name}探索得更多？"[:30],"options":["爸爸妈妈","祖辈家人","大家轮流","其他陪伴"],"allow_text":True,"placeholder":"最常一起做什么？"},
            {"id":"g2","category":"期待","lead":"关于期待——","question":f"最希望{name}在哪方面多尝试？"[:30],"options":["表达想法","动手解决","理解伙伴","认识自己"],"allow_text":True,"placeholder":"写下一件期待的小事"},
            {"id":"g3","category":"在意","lead":"最近在意——","question":f"最近最想多了解{name}什么？"[:30],"options":["兴趣变化","遇难反应","合作方式","还没想好"],"allow_text":True,"placeholder":"可以写下最近的观察"},
        ],
        "dimension_questions": dimension_questions,
    }


def generate_report_snapshot(child_name: str, events: list[dict], child_age: int = 0) -> tuple[dict, dict]:
    """默认走 Core 内置规则；配置 REPORT_AGENT_URL 时可保留独立服务作回归对照。"""
    url = os.environ.get("REPORT_AGENT_URL", "http://127.0.0.1:8030/api/report/generate").strip()
    if not url:
        report = generate_internal_report(child_name, events)
        report["questions"] = fallback_report_questions(child_name, report, events)
        return report, {"generatorVersion": "core-rule-analyzer-v1", "rulesetVersion": "core-rules-v1", "promptVersion": None, "modelId": None}
    request = urlrequest.Request(url, data=json.dumps({"child_name": child_name, "child_age": child_age, "events": events}, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=50) as response:
            report = json.loads(response.read().decode("utf-8"))
            return report, {"generatorVersion": "report-agent-http-v1", "rulesetVersion": "rule-or-llm-v1", "promptVersion": None, "modelId": os.environ.get("REPORT_LLM_MODEL") or None}
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError):
        logger.exception("报告智能体暂不可用，改用 Core 安全报告")
        report = generate_internal_report(child_name, events)
        report["questions"] = fallback_report_questions(child_name, report, events)
        return report, {"generatorVersion": "core-rule-analyzer-v1", "rulesetVersion": "core-rules-v1", "promptVersion": None, "modelId": None}


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "ai-bole-platform-core",
        "moduleAccessPolicy": "all-students",
    }


@app.get("/api/v1/modules")
def list_modules_v1() -> dict:
    """V1 模块目录：保留旧 Portal 配置，待其迁移后成为唯一入口。"""
    return {"contractVersion": "1.0", "modules": load_module_catalog()}


@app.post("/api/v1/assessment-sessions", status_code=201)
def create_assessment_session(payload: AssessmentSessionIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """创建会话并签发一次性启动码；session ID 从不作为模块凭据。"""
    account = require_student_viewer(ai_bole_session)
    manifest = module_manifest(payload.module_id)
    timestamp = now_iso()
    session_id = str(uuid.uuid4())
    launch_code = secrets.token_urlsafe(32)
    # 独立体验通常需要几分钟到几十分钟。启动码此前仅 60 秒有效，
    # 而聊天、故事和深海都在“完成”时才连接 SDK，导致真实完成记录永远无法回写。
    # 启动码仍然只能兑换一次，但有效期覆盖一次完整体验。
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        # targetAge 只描述内容设计时参考的年龄段，不能作为学生进入模块的权限门槛。
        # 统一平台中的任意学生账号都可以启动全部四个探索模块；年龄仅供模块调整
        # 表达方式和后续观察解释使用。
        db.execute(
            """INSERT INTO assessment_sessions
               (id,child_profile_id,module_id,module_version,status,created_at)
               VALUES (?,?,?,?,?,?)""",
            (session_id, profile["id"], manifest["id"], manifest["version"], "created", timestamp),
        )
        db.execute(
            """INSERT INTO module_authorizations
               (id,session_id,launch_code_hash,launch_expires_at,scopes_json)
               VALUES (?,?,?,?,?)""",
            (str(uuid.uuid4()), session_id, token_digest(launch_code), expires,
             json.dumps(["evidence:write", "artifact:write", "session:complete", "session:interrupt"])),
        )
    avatar_id = account["avatar_id"] or "student-1"
    return {"sessionId": session_id, "moduleId": manifest["id"], "moduleVersion": manifest["version"], "launchCode": launch_code, "launchCodeExpiresAt": expires, "returnUrl": "http://localhost:4173/?from=module", "contractVersion": "1.0", "student": {"id": account["id"], "displayName": account["display_name"], "age": profile["age"], "avatarId": avatar_id, "avatarUrl": f"http://localhost:3000/assets/avatars/student/{avatar_id}.png"}}


@app.post("/api/v1/module-authorizations:exchange")
def exchange_module_authorization(payload: LaunchCodeExchangeIn) -> dict:
    timestamp = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    token = secrets.token_urlsafe(32)
    with connect() as db:
        row = db.execute(
            """SELECT a.*, s.status FROM module_authorizations a
               JOIN assessment_sessions s ON s.id=a.session_id
               WHERE a.launch_code_hash=? AND a.launch_expires_at>? AND a.exchanged_at IS NULL""",
            (token_digest(payload.launch_code), timestamp),
        ).fetchone()
        if not row or row["status"] not in {"created", "interrupted"}:
            raise HTTPException(401, "启动授权已失效")
        updated = db.execute("UPDATE module_authorizations SET exchanged_at=?,token_hash=?,expires_at=? WHERE id=? AND exchanged_at IS NULL", (timestamp, token_digest(token), expires, row["id"])).rowcount
        if updated != 1: raise HTTPException(401, "启动授权已失效")
        if row["status"] == "created":
            db.execute("UPDATE assessment_sessions SET status='active',started_at=?,state_version=state_version+1 WHERE id=?", (timestamp, row["session_id"]))
    return {"token": token, "tokenType": "Bearer", "expiresAt": expires}


@app.get("/api/v1/module-authorizations:identity")
def module_authorization_identity(authorization: str | None = Header(default=None)) -> dict:
    """Resolve a verified module token to its student owner."""
    auth = require_module_authorization(authorization)
    return {
        "studentId": auth["child_profile_id"],
        "sessionId": auth["session_id"],
        "moduleId": auth["module_id"],
    }


@app.patch("/api/v1/assessment-sessions/{session_id}")
def change_assessment_session(session_id: str, payload: SessionStatusIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if auth["session_id"] != session_id:
        raise HTTPException(403, "模块授权不属于该探索会话")
    required_scope = "session:complete" if payload.status == "completed" else "session:interrupt"
    if required_scope not in json.loads(auth["scopes_json"]): raise HTTPException(403, "模块授权不含会话状态权限")
    # 中断（如页面刷新触发的 pagehide 中断）后允许补记完成，
    # 与证据写入规则一致：interrupted 会话仍可写入证据并落档。
    allowed = {"active": {"completed", "interrupted", "abandoned"}, "interrupted": {"active", "completed", "abandoned"}}
    timestamp = now_iso()
    with connect() as db:
        session = db.execute("SELECT * FROM assessment_sessions WHERE id=?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(404, "探索会话不存在")
        if session["status"] == payload.status:
            return {"id": session_id, "status": session["status"], "duplicate": True}
        if payload.status not in allowed.get(session["status"], set()):
            raise HTTPException(409, "SESSION_TRANSITION_INVALID")
        if payload.state_version is not None and payload.state_version != session["state_version"]:
            raise HTTPException(409, "SESSION_STATE_CONFLICT")
        ended_at = timestamp if payload.status in {"completed", "abandoned"} else None
        active_seconds = session["active_seconds"]
        if ended_at and session["started_at"]:
            active_seconds += max(0, int((datetime.fromisoformat(ended_at) - datetime.fromisoformat(session["started_at"])).total_seconds()))
        db.execute(
            """UPDATE assessment_sessions
               SET status=?,ended_at=?,active_seconds=?,summary_json=?,interruption_reason=?,state_version=state_version+1
               WHERE id=?""",
            (payload.status, ended_at, active_seconds, json.dumps(payload.summary, ensure_ascii=False), payload.reason, session_id),
        )
        if ended_at: db.execute("UPDATE module_authorizations SET revoked_at=? WHERE session_id=? AND revoked_at=''", (timestamp, session_id))
    return {"id": session_id, "status": payload.status, "duplicate": False}


@app.post("/api/v1/evidence-events:batch")
def create_evidence_events_v1(payload: EvidenceBatchIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if "evidence:write" not in json.loads(auth["scopes_json"]): raise HTTPException(403, "模块授权不含证据写入权限")
    if auth["status"] not in {"active", "interrupted"}:
        raise HTTPException(409, "探索会话当前不能写入证据")
    manifest = module_manifest(auth["module_id"])
    saved: list[dict] = []
    with connect() as db:
        for event in payload.events:
            if event.event_type not in manifest["supportedEventTypes"]:
                raise HTTPException(422, "该模块版本不支持此事件类型")
            validate_evidence_event(event)
            policy = policy_for_event(event.event_type)
            event_id = str(uuid.uuid4())
            try:
                db.execute(
                    """INSERT INTO source_events
                       (id,session_id,idempotency_key,event_type,schema_version,payload_json,sequence_no,occurred_at,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (event_id, auth["session_id"], event.idempotency_key, event.event_type, event.schema_version,
                     json.dumps(event.payload, ensure_ascii=False), event.sequence_no, event.occurred_at, now_iso()),
                )
            except sqlite3.IntegrityError:
                existing = db.execute("SELECT id FROM source_events WHERE session_id=? AND idempotency_key=?", (auth["session_id"], event.idempotency_key)).fetchone()
                saved.append({"eventId": existing["id"], "duplicate": True})
                continue
            evidence_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO evidence_records
                   (id,source_event_id,evidence_level,constructs_json,behavior_summary,policy_version,construct_registry_version,derived_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (evidence_id, event_id, policy["evidenceLevel"], json.dumps(policy["constructs"], ensure_ascii=False),
                 policy["behaviorSummary"], policy["policyVersion"], policy["constructRegistryVersion"], now_iso()),
            )
            saved.append({"eventId": event_id, "evidenceId": evidence_id, "duplicate": False})
    return {"saved": saved}


@app.post("/api/v1/artifacts", status_code=201)
def create_artifact_v1(payload: ArtifactIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if "artifact:write" not in json.loads(auth["scopes_json"]): raise HTTPException(403, "模块授权不含作品写入权限")
    validate_schema("artifact.v1.schema.json", payload.model_dump(by_alias=True, exclude_none=True), "作品无效")
    with connect() as db:
        if payload.preview_resource_id and not db.execute(
            "SELECT 1 FROM snapshot_assets WHERE id=? AND session_id=?",
            (payload.preview_resource_id, auth["session_id"]),
        ).fetchone():
            raise HTTPException(422, "作品预览不属于当前探索会话")
        # 校验 source_resource_id（如 story:{id}）必须归属当前探索会话对应的孩子，
        # 防止学生通过 source_resource_id 把别人的故事全文塞进自己的报告。
        story_ref = re.fullmatch(r"story:(\d+)", str(payload.source_resource_id or ""))
        if story_ref:
            owner = db.execute(
                "SELECT child_profile_id FROM assessment_sessions WHERE id=?",
                (auth["session_id"],),
            ).fetchone()
            if owner and STORY_DB_PATH.exists():
                try:
                    with sqlite3.connect(STORY_DB_PATH) as story_db:
                        story_db.row_factory = sqlite3.Row
                        story_owner = story_db.execute(
                            "SELECT c.owner_id FROM stories s JOIN characters c ON s.character_id=c.id WHERE s.id=?",
                            (int(story_ref.group(1)),),
                        ).fetchone()
                except sqlite3.Error:
                    story_owner = None
                if not story_owner or not story_owner["owner_id"] or story_owner["owner_id"] != owner["child_profile_id"]:
                    raise HTTPException(422, "作品引用了不属于当前孩子的故事内容")
        existing = db.execute(
            "SELECT session_id FROM artifacts WHERE id=?", (payload.artifact_id,)
        ).fetchone()
        if existing and existing["session_id"] != auth["session_id"]:
            raise HTTPException(409, "作品标识已被其他探索会话使用")
        db.execute(
            """INSERT INTO artifacts
               (id,session_id,type,title,summary,preview_resource_id,source_resource_id,created_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 type=excluded.type,title=excluded.title,summary=excluded.summary,
                 preview_resource_id=excluded.preview_resource_id,
                 source_resource_id=excluded.source_resource_id,created_at=excluded.created_at""",
            (payload.artifact_id, auth["session_id"], payload.type, payload.title,
             payload.summary, payload.preview_resource_id, payload.source_resource_id,
             payload.created_at),
        )
    return {"id": payload.artifact_id, "created": existing is None, "updated": existing is not None}


def _nonnegative_int(*values: object) -> int:
    for value in values:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            continue
    return 0


def _short_highlight_quote(value: object, limit: int = 42) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n。！？!?，,")
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[:limit - 1].rstrip()}…"


def artifact_highlight_reason(
    module_id: str,
    title: str,
    session_summary: dict,
    event_payloads: list[dict],
    behavior_summaries: list[str],
) -> str:
    """根据作品所属会话的真实过程数据解释其入选原因，不复述作品摘要。"""
    if module_id == "chat":
        turns = _nonnegative_int(
            session_summary.get("turnCount"),
            *(payload.get("turnCount") for payload in event_payloads),
        )
        chars = _nonnegative_int(session_summary.get("totalChildChars"))
        long_turns = _nonnegative_int(session_summary.get("longTurnCount"))
        child_turns = [
            item.get("text", "")
            for payload in event_payloads
            for item in payload.get("childTurns", [])
            if isinstance(item, dict)
        ]
        quote = _short_highlight_quote(max(child_turns, key=lambda value: len(str(value)), default=""))
        details = []
        if turns:
            details.append(f"连续表达了 {turns} 轮")
        if chars:
            details.append(f"一共说出 {chars} 个字")
        if long_turns:
            details.append(f"其中有 {long_turns} 次较完整的长表达")
        reason = "，".join(details)
        if quote:
            reason += ("；" if reason else "") + f"还具体说到“{quote}”"
        if reason:
            return f"这次聊天中，孩子{reason}。这些清楚、可回看的表达过程让它成为本次聊天高光。"

    if module_id == "story":
        contributions = max(
            [_nonnegative_int(payload.get("contributionCount")) for payload in event_payloads] or [0]
        )
        ending_length = _nonnegative_int(session_summary.get("endingLength"))
        ideas = session_summary.get("childIdeas", [])
        quote = _short_highlight_quote(
            max(ideas, key=lambda value: len(str(value)), default="") if isinstance(ideas, list) else ""
        )
        details = []
        if contributions:
            details.append(f"连续贡献了 {contributions} 个故事片段")
        if ending_length:
            details.append(f"并自己完成了 {ending_length} 字的结尾")
        if quote:
            details.append(f"还主动补充了“{quote}”这样的具体情节")
        if details:
            return f"在《{title}》的创作中，孩子{'，'.join(details)}，因此被收藏为这次故事共创的高光。"

    if module_id == "deep_sea":
        completion_payload = next(
            (payload for payload in event_payloads if payload.get("totalLevels") == 3), {}
        )
        completed = _nonnegative_int(
            completion_payload.get("completedLevels"), session_summary.get("completedLevels")
        )
        total = _nonnegative_int(completion_payload.get("totalLevels"), session_summary.get("totalLevels")) or 3
        adjustments = _nonnegative_int(
            completion_payload.get("adjustmentCount"), session_summary.get("meaningfulAdjustments")
        )
        pair_count = max(
            [_nonnegative_int(payload.get("successfulPairs")) for payload in event_payloads] or [0]
        )
        details = []
        if completed:
            task_names = "生态配对、能源线路和角色协商" if completed == total == 3 else f"{completed}/{total} 项基地任务"
            details.append(f"完成了{task_names}")
        if pair_count:
            details.append(f"成功完成 {pair_count} 组生态配对")
        if adjustments:
            details.append(f"还根据结果进行了 {adjustments} 次调整")
        if details:
            return f"这次重建中，孩子{'，'.join(details)}。作品保留了完整的解决过程，因此成为深海高光。"

    if module_id == "career":
        payload = event_payloads[-1] if event_payloads else {}
        career_name = _short_highlight_quote(session_summary.get("careerName"), 24)
        completed = _nonnegative_int(session_summary.get("completedStages"), session_summary.get("stages"))
        total = _nonnegative_int(session_summary.get("stageCount"))
        attempts = _nonnegative_int(payload.get("attemptCount"))
        adjustments = _nonnegative_int(payload.get("adjustmentCount"))
        details = []
        if completed:
            details.append(f"完成了 {completed}/{total} 个阶段" if total else f"完成了 {completed} 个职业阶段")
        if attempts:
            details.append(f"主动尝试了 {attempts} 次")
        if adjustments:
            details.append(f"并根据反馈调整了 {adjustments} 次")
        if details:
            subject = f"在“{career_name}”体验中" if career_name else f"在《{title}》中"
            return f"{subject}，孩子{'，'.join(details)}。这份完整的参与记录让它成为职业体验高光。"

    distinct_evidence = next(
        (text.strip() for text in behavior_summaries if text and text.strip()), ""
    )
    if distinct_evidence:
        return f"《{title}》同时留下了“{distinct_evidence}”的过程证据，因此被收藏为值得回看的高光作品。"
    fallback = {
        "chat": "这次对话留下了连续、可回看的真实表达，因此被收藏为本次聊天高光。",
        "story": f"《{title}》记录了从想法到完成作品的创作过程，因此被收藏为本次故事高光。",
        "deep_sea": "这件作品记录了任务完成和解决问题的过程，因此被收藏为本次重建高光。",
        "career": f"《{title}》记录了完整参与职业任务的过程，因此被收藏为本次体验高光。",
    }
    return fallback.get(module_id, f"《{title}》留下了可回看的完成过程，因此被收藏为高光作品。")


@app.get("/api/v1/artifacts")
def list_artifacts_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = db.execute("""SELECT a.*, s.module_id, s.module_version, s.summary_json FROM artifacts a
                           JOIN assessment_sessions s ON s.id=a.session_id
                           WHERE s.child_profile_id=? ORDER BY a.created_at DESC""", (profile["id"],)).fetchall()
        evidence_rows = db.execute(
            """SELECT se.session_id,se.payload_json,er.behavior_summary
               FROM source_events se JOIN evidence_records er ON er.source_event_id=se.id
               JOIN assessment_sessions s ON s.id=se.session_id
               WHERE s.child_profile_id=? ORDER BY se.occurred_at""",
            (profile["id"],),
        ).fetchall()
        manual_rows = db.execute(
            "SELECT * FROM manual_works WHERE student_account_id=? ORDER BY created_at DESC",
            (account["id"],),
        ).fetchall()
        comment_rows = db.execute(
            """SELECT c.*,a.display_name AS author_name,a.adult_kind AS author_kind
               FROM work_comments c JOIN accounts a ON a.id=c.author_account_id
               WHERE c.student_account_id=? ORDER BY c.created_at""",
            (account["id"],),
        ).fetchall()
    comments: dict[str, list[dict]] = {}
    for row in comment_rows:
        comments.setdefault(row["work_id"], []).append({
            "id": row["id"], "body": row["body"], "authorName": row["author_name"],
            "authorKind": row["author_kind"], "createdAt": row["created_at"],
        })
    session_evidence: dict[str, dict[str, list]] = {}
    for row in evidence_rows:
        context = session_evidence.setdefault(row["session_id"], {"payloads": [], "summaries": []})
        try:
            context["payloads"].append(json.loads(row["payload_json"] or "{}"))
        except json.JSONDecodeError:
            logger.warning("作品高光原因跳过了无效事件 payload：%s", row["session_id"])
        context["summaries"].append(row["behavior_summary"] or "")
    artifacts = [{
        "id": row["id"], "sessionId": row["session_id"], "moduleId": row["module_id"],
        "moduleVersion": row["module_version"], "type": row["type"], "kind": "highlight",
        "title": row["title"], "summary": row["summary"], "detail": row["summary"],
        "highlightReason": artifact_highlight_reason(
            row["module_id"], row["title"], json.loads(row["summary_json"] or "{}"),
            session_evidence.get(row["session_id"], {}).get("payloads", []),
            session_evidence.get(row["session_id"], {}).get("summaries", []),
        ),
        "previewResourceId": row["preview_resource_id"], "sourceResourceId": row["source_resource_id"],
        "createdAt": row["created_at"], "comments": comments.get(row["id"], []),
    } for row in rows]
    artifact_sources = {
        (row["module_id"], row["source_resource_id"])
        for row in rows if row["source_resource_id"]
    }
    artifacts.extend({
        "id": f"manual-{row['id']}", "sessionId": None, "moduleId": row["module"],
        "moduleVersion": None, "type": "manual", "kind": "manual_work", "title": row["title"],
        "summary": manual_work_summary(row), "detail": row["description"] or "这件作品由我自己添加到作品册。",
        "workType": manual_work_type_key(row),
        "previewResourceId": None, "sourceResourceId": row["source_id"] or None, "createdAt": row["created_at"],
        "comments": comments.get(f"manual-{row['id']}", []),
    } for row in manual_rows if (row["module"], row["source_id"]) not in artifact_sources)
    artifacts.sort(key=lambda item: item["createdAt"], reverse=True)
    return {"account": public_account(account), "viewer": public_account(viewer), "artifacts": artifacts}


def evidence_rows_for_profile(db: sqlite3.Connection, profile_id: str, limit: int = 500) -> list[sqlite3.Row]:
    return db.execute(
        """SELECT er.id,se.id AS source_event_id,se.session_id,se.event_type,se.payload_json,se.occurred_at,
                  er.evidence_level,er.constructs_json,er.behavior_summary,s.module_id,s.module_version,s.summary_json,
                  (SELECT a.preview_resource_id FROM artifacts a WHERE a.session_id=s.id AND a.preview_resource_id IS NOT NULL ORDER BY a.created_at DESC LIMIT 1) AS preview_resource_id,
                  (SELECT a.title FROM artifacts a WHERE a.session_id=s.id ORDER BY a.created_at DESC LIMIT 1) AS artifact_title,
                  (SELECT a.summary FROM artifacts a WHERE a.session_id=s.id ORDER BY a.created_at DESC LIMIT 1) AS artifact_summary
           FROM evidence_records er JOIN source_events se ON se.id=er.source_event_id
           JOIN assessment_sessions s ON s.id=se.session_id
           WHERE s.child_profile_id=? ORDER BY se.occurred_at DESC, er.derived_at DESC LIMIT ?""",
        (profile_id, max(1, min(limit, 500))),
    ).fetchall()


@app.get("/api/v1/evidence-records")
def list_evidence_records_v1(limit: int = 200, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = evidence_rows_for_profile(db, profile["id"], limit)
    dimensions = construct_dimension_map()
    return {"records": [{
        "id": row["id"], "sourceEventId": row["source_event_id"], "sessionId": row["session_id"],
        "moduleId": row["module_id"], "moduleVersion": row["module_version"], "eventType": row["event_type"],
        "occurredAt": row["occurred_at"], "evidenceLevel": row["evidence_level"],
        "constructs": json.loads(row["constructs_json"]),
        "reportDimensions": evidence_report_dimensions(row, dimensions),
        "behaviorSummary": row["behavior_summary"], "payload": json.loads(row["payload_json"]),
        "sessionSummary": json.loads(row["summary_json"] or "{}"),
        "artifactTitle": row["artifact_title"], "artifactSummary": row["artifact_summary"],
        "previewResourceId": row["preview_resource_id"],
        "previewUrl": f"http://localhost:8020/api/v1/assets/snapshots/{row['preview_resource_id']}" if row["preview_resource_id"] else None,
    } for row in rows]}


@app.get("/api/v1/talents")
def list_talents_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = evidence_rows_for_profile(db, profile["id"], 500)
        completed_modules = {
            row["module_id"] for row in db.execute(
                "SELECT DISTINCT module_id FROM assessment_sessions WHERE child_profile_id=? AND status='completed'",
                (profile["id"],),
            ).fetchall()
        }
    return {
        "rule": "完成星星所属大陆的一次完整体验后，该星星进入可点亮状态；证据强度仅用于报告分析。",
        "talents": build_talent_eligibility(rows, completed_modules),
    }


@app.post("/api/v1/talent-stories")
def create_talent_stories_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """藏宝图专用生成链路：按大陆归属送入真实游戏记录，不复用成人报告的维度归类。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        events, _ = standard_events_for_report(db, profile["id"])
        completed_modules = {row["module_id"] for row in db.execute(
            "SELECT DISTINCT module_id FROM assessment_sessions WHERE child_profile_id=? AND status='completed'",
            (profile["id"],),
        ).fetchall()}
    star_events = []
    for event in events:
        if event["module"] not in completed_modules:
            continue
        dimensions = treasure_dimensions_for_event(event)
        if dimensions:
            star_events.append({**event, "intelligence_candidates": sorted(dimensions)})
    report, generator = generate_report_snapshot(profile["display_name"], star_events, int(profile["age"] or 0))
    level_one_events = [event for event in star_events if event["module"] == "deep_sea"
                        and event["event_type"] == "deep-sea.spatial-task-completed.v1"
                        and int(event["raw_evidence"].get("level", 0)) == 1]
    if level_one_events:
        reviews = []
        for event in level_one_events[-3:]:
            raw = event["raw_evidence"]
            context = event.get("context", {}) if isinstance(event.get("context"), dict) else {}
            summary = context.get("sessionSummary", {}) if isinstance(context.get("sessionSummary"), dict) else {}
            review = summary.get("levelOneReview", {}) if isinstance(summary.get("levelOneReview"), dict) else {}
            pairs = [str(item).strip() for item in review.get("matchedRelationships", []) if str(item).strip()] if isinstance(review.get("matchedRelationships"), list) else []
            successful, total = int(raw.get("successfulPairs", 0)), int(raw.get("totalPairs", 4))
            checks = raw.get("checkAttempts")
            result = "完成了全部配对" if successful == total else f"完成了 {successful}/{total} 组配对"
            pair_text = f"，为{'、'.join(pairs)}找到了合适的位置" if pairs else "，按照栖息地和共生关系安排生物住处"
            check_text = f"，经过 {checks} 次检查" if checks is not None else ""
            reviews.append(f"你在第一关“珊瑚公寓”里{pair_text}{check_text}，{result}")
        exact_story = (f"你体验了 {len(level_one_events)} 次深海第一关。" if len(level_one_events) > 1 else "") + "；".join(reviews) + "。"
        for item in report["dimensions"]:
            if item["key"] == "naturalistic":
                item["child_story"] = exact_story
                item["evidence_refs"] = [event["id"] for event in level_one_events if event.get("id")]
    return {
        "generatedAt": report["generated_at"],
        "generator": generator["generatorVersion"],
        "stories": [{"key": item["key"], "story": item["child_story"], "evidenceRefs": item["evidence_refs"]}
                    for item in report["dimensions"] if item["key"] in CANONICAL_INTELLIGENCES],
    }


def timeline_session_caption(module_id: str, summary: dict, evidence_count: int) -> str:
    """把一次会话压缩成家长能读懂的过程事实，不复述作品内容。"""
    if module_id == "chat":
        turns = _nonnegative_int(summary.get("turnCount"))
        long_turns = _nonnegative_int(summary.get("longTurnCount"))
        if turns:
            extra = f"，其中有 {long_turns} 次较完整表达" if long_turns else ""
            return f"完成 {turns} 轮连续对话{extra}"
    if module_id == "story":
        title = _short_highlight_quote(summary.get("storyTitle"), 28)
        ideas = summary.get("childIdeas", [])
        idea_count = len(ideas) if isinstance(ideas, list) else 0
        subject = f"《{title}》" if title else "一次故事"
        extra = f"，主动贡献了 {idea_count} 个想法" if idea_count else ""
        return f"完成{subject}的共创{extra}"
    if module_id == "deep_sea":
        completed = _nonnegative_int(summary.get("completedLevels"))
        if completed:
            return f"完成 {completed} 处基地任务，留下配对、布局与协商的解决过程"
    if module_id == "career":
        career_name = _short_highlight_quote(summary.get("careerName"), 20)
        completed = _nonnegative_int(summary.get("completedStages"), summary.get("stages"))
        total = _nonnegative_int(summary.get("stageCount"))
        subject = f"“{career_name}”体验" if career_name else "一次职业体验"
        if completed:
            stages = f"{completed}/{total} 个阶段" if total else f"{completed} 个阶段"
            return f"完成{subject}的 {stages}"
    if evidence_count:
        return f"完成一次探索，留下 {evidence_count} 条可回看的过程记录"
    return "完成一次探索，为成长星路添上一个新脚印"


@app.get("/api/v1/timeline")
def timeline_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = db.execute("""SELECT s.id,s.module_id,s.module_version,s.status,s.started_at,s.ended_at,s.active_seconds,s.summary_json,
                           (SELECT COUNT(*) FROM source_events e WHERE e.session_id=s.id) AS evidence_count,
                           (SELECT COUNT(*) FROM artifacts a WHERE a.session_id=s.id) AS artifact_count
                           FROM assessment_sessions s
                           WHERE s.child_profile_id=? AND s.status='completed'
                           ORDER BY COALESCE(s.ended_at,s.started_at,s.created_at) DESC""", (profile["id"],)).fetchall()
        observation_rows = db.execute(
            """SELECT s.id AS session_id,s.module_id,er.constructs_json,
                      er.behavior_summary,se.occurred_at
               FROM evidence_records er JOIN source_events se ON se.id=er.source_event_id
               JOIN assessment_sessions s ON s.id=se.session_id
               WHERE s.child_profile_id=? AND s.status='completed' AND TRIM(er.behavior_summary)<>''
               ORDER BY se.occurred_at DESC""",
            (profile["id"],),
        ).fetchall()
    sessions = []
    for row in rows:
        try:
            summary = json.loads(row["summary_json"] or "{}")
        except json.JSONDecodeError:
            logger.warning("成长足迹跳过了无效会话摘要：%s", row["id"])
            summary = {}
        sessions.append({
            "id": row["id"], "moduleId": row["module_id"], "moduleVersion": row["module_version"],
            "status": row["status"], "startedAt": row["started_at"], "endedAt": row["ended_at"],
            "activeSeconds": row["active_seconds"] or 0, "evidenceCount": row["evidence_count"],
            "artifactCount": row["artifact_count"],
            "caption": timeline_session_caption(row["module_id"], summary, row["evidence_count"]),
        })
    module_observations: dict[str, list[str]] = {}
    session_observations: dict[str, list[str]] = {}
    signal_stats: dict[str, dict] = {}
    construct_names = construct_display_name_map()
    for row in observation_rows:
        text = re.sub(r"\s+", " ", row["behavior_summary"] or "").strip()
        items = module_observations.setdefault(row["module_id"], [])
        if text and text not in items and len(items) < 3:
            items.append(text)
        session_items = session_observations.setdefault(row["session_id"], [])
        if text and text not in session_items and len(session_items) < 3:
            session_items.append(text)
        try:
            constructs = json.loads(row["constructs_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            constructs = []
        for key in constructs:
            if key not in construct_names:
                continue
            signal = signal_stats.setdefault(key, {
                "key": key,
                "label": construct_names[key],
                "evidenceCount": 0,
                "modules": set(),
                "firstSeenAt": row["occurred_at"],
                "lastSeenAt": row["occurred_at"],
                "observation": text,
            })
            signal["evidenceCount"] += 1
            signal["modules"].add(row["module_id"])
            signal["firstSeenAt"] = min(signal["firstSeenAt"], row["occurred_at"])
            signal["lastSeenAt"] = max(signal["lastSeenAt"], row["occurred_at"])
    for session in sessions:
        session["observations"] = session_observations.get(session["id"], [])
    grouped: dict[str, list[dict]] = {}
    for session in sessions:
        grouped.setdefault(session["moduleId"], []).append(session)
    module_summaries = []
    for module_id, items in grouped.items():
        ordered = sorted(items, key=lambda item: item["endedAt"] or item["startedAt"] or "")
        module_summaries.append({"moduleId": module_id, "completedCount": len(items), "firstUsedAt": ordered[0]["startedAt"] or ordered[0]["endedAt"], "lastUsedAt": ordered[-1]["endedAt"] or ordered[-1]["startedAt"], "activeSeconds": sum(item["activeSeconds"] for item in items), "evidenceCount": sum(item["evidenceCount"] for item in items), "artifactCount": sum(item["artifactCount"] for item in items), "observations": module_observations.get(module_id, []), "recentSessions": list(reversed(ordered))[:3]})
    long_term_signals = []
    for signal in signal_stats.values():
        modules = sorted(signal.pop("modules"))
        module_count = len(modules)
        evidence_count = signal["evidenceCount"]
        status = (
            "跨情境出现"
            if module_count >= 2
            else "反复出现"
            if evidence_count >= 3
            else "正在积累"
        )
        long_term_signals.append({
            **signal,
            "modules": modules,
            "moduleCount": module_count,
            "status": status,
        })
    long_term_signals.sort(
        key=lambda item: (item["moduleCount"], item["evidenceCount"], item["lastSeenAt"]),
        reverse=True,
    )
    return {
        "sessions": sessions,
        "moduleSummaries": module_summaries,
        "longTermSignals": long_term_signals[:6],
    }


@app.get("/api/v1/assessment-sessions/{session_id}")
def read_assessment_session(session_id: str, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        row = db.execute("SELECT * FROM assessment_sessions WHERE id=? AND child_profile_id=?", (session_id, profile["id"])).fetchone()
    if not row: raise HTTPException(404, "探索会话不存在")
    return {"id": row["id"], "moduleId": row["module_id"], "moduleVersion": row["module_version"], "status": row["status"], "createdAt": row["created_at"], "startedAt": row["started_at"], "endedAt": row["ended_at"], "activeSeconds": row["active_seconds"], "stateVersion": row["state_version"], "summary": json.loads(row["summary_json"] or "{}"), "reason": row["interruption_reason"]}


def report_has_current_reflection(report: dict) -> bool:
    dimensions = report.get("dimensions", [])
    questions = report.get("questions", {})
    if len(dimensions) != 6 or not isinstance(questions, dict):
        return False
    if questions.get("question_version") != REPORT_QUESTION_VERSION:
        return False
    if report.get("analysis_version") != REPORT_ANALYSIS_VERSION:
        return False
    dimension_questions = questions.get("dimension_questions")
    global_questions = questions.get("global_questions")
    if not isinstance(dimension_questions, list) or not isinstance(global_questions, list) or len(global_questions) != 3:
        return False
    has_dimension_evidence = any(
        isinstance(item, dict) and bool(item.get("evidence_refs"))
        for item in dimensions
    )
    return not has_dimension_evidence or bool(dimension_questions)


@app.post("/api/v1/reports")
def create_report_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """报告生成实现仍可独立部署，但证据读取和快照保存只经过 Core。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        events, evidence_ids = standard_events_for_report(db, profile["id"])
        # 缓存键里带上分析规则版本。否则报告文案升级后，证据没变的孩子会一直
        # 看到上一版生成的旧报告，“已修复”对家长端不生效。
        evidence_hash = hashlib.sha256(
            f"{ANALYSIS_VERSION}:{json.dumps(events, ensure_ascii=False, sort_keys=True)}".encode("utf-8")
        ).hexdigest()
        cached = db.execute(
            "SELECT id,status,report_json FROM reports WHERE child_profile_id=? AND evidence_set_hash=? AND status='published' ORDER BY published_at DESC LIMIT 1",
            (profile["id"], evidence_hash),
        ).fetchone()
    if cached:
        cached_report = json.loads(cached["report_json"])
        if report_has_current_reflection(cached_report):
            cached_report["report_id"] = cached["id"]
            return {"id": cached["id"], "status": cached["status"], "report": cached_report, "cached": True}
    report, generator = generate_report_snapshot(profile["display_name"], events, int(profile["age"] or 0))
    timestamp = now_iso()
    with connect() as db:
        report_id = str(uuid.uuid4())
        report["report_id"] = report_id
        db.execute(
            """INSERT INTO reports
               (id,child_profile_id,generator_version,ruleset_version,prompt_version,model_id,evidence_set_hash,status,report_json,generated_at,published_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (report_id, profile["id"], generator["generatorVersion"], generator["rulesetVersion"], generator["promptVersion"], generator["modelId"], evidence_hash, "published", json.dumps(report, ensure_ascii=False), timestamp, timestamp),
        )
        db.executemany("INSERT INTO report_evidence_links (report_id,evidence_record_id,section_key) VALUES (?,?,?)", [(report_id, evidence_id, "report") for evidence_id in evidence_ids])
    return {"id": report_id, "status": "published", "report": report}


@app.get("/api/v1/reports/latest-published")
def latest_published_report_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        row = db.execute("SELECT * FROM reports WHERE child_profile_id=? AND status='published' ORDER BY published_at DESC LIMIT 1", (profile["id"],)).fetchone()
    if not row:
        raise HTTPException(404, "还没有已发布的报告")
    report = json.loads(row["report_json"])
    report["report_id"] = row["id"]
    return {"id": row["id"], "status": row["status"], "generatedAt": row["generated_at"], "report": report}


@app.post("/api/v1/reports/{report_id}/parent-feedback")
def save_parent_feedback_v1(report_id: str, payload: ParentFeedbackIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "只有老师/家长可以补充家庭观察")
    student = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, student["id"])
        row = db.execute("SELECT * FROM reports WHERE id=? AND child_profile_id=?", (report_id, profile["id"])).fetchone()
    if not row:
        raise HTTPException(404, "没有找到这份报告")
    report = json.loads(row["report_json"])
    dimension = next((item for item in report.get("dimensions", []) if item.get("key") == payload.dimension_key), None)
    if not dimension:
        raise HTTPException(400, "报告中没有这个观察维度")
    report_questions = report.get("questions", {})
    dimension_questions = [item for item in report_questions.get("dimension_questions", []) if item.get("key") == payload.dimension_key]
    trusted_questions = [*dimension_questions, *report_questions.get("global_questions", [])]
    # 兼容旧报告：旧快照可能尚未保存 questions。此时接受前端根据该报告
    # 维度生成的有限兜底问题，使家长的真实回答仍能进入专属建议流程。
    if not dimension_questions:
        supplied_questions = [
            {
                "id": str(item.get("id", ""))[:32],
                "key": str(item.get("key", ""))[:64] or None,
                "category": str(item.get("category", ""))[:32] or None,
                "lead": str(item.get("lead", ""))[:20],
                "question": str(item.get("question", ""))[:120],
                "options": [str(option)[:40] for option in (item.get("options") if isinstance(item.get("options"), list) else [])[:4]],
                "allow_text": True,
                "placeholder": str(item.get("placeholder", ""))[:60],
            }
            for item in payload.questions[:8]
            if isinstance(item, dict)
            and str(item.get("id", "")).strip()
            and (not item.get("key") or item.get("key") == payload.dimension_key)
        ]
        trusted_questions = [*supplied_questions, *report_questions.get("global_questions", [])]
    trusted_ids = {str(item.get("id", "")) for item in trusted_questions}
    trusted_answers = []
    for answer in payload.answers:
        question_id = str(answer.get("question_id") or answer.get("id") or "")
        if question_id in trusted_ids:
            trusted_answers.append({"question_id": question_id, "selected": str(answer.get("selected", ""))[:120], "text": str(answer.get("text", ""))[:500]})
    agent_url = os.environ.get("REPORT_AGENT_URL", "http://127.0.0.1:8030/api/report/generate").strip()
    suggestion_url = agent_url.rsplit("/", 1)[0] + "/suggestions"
    request_body = {"dimension":{"key":dimension["key"],"name":dimension.get("name", dimension["key"])},"child":{"childName":profile["display_name"],"age":profile["age"]},"evidence":{"analysis":dimension.get("analysis", ""),"evidence_brief":dimension_questions},"questions":trusted_questions,"answers":trusted_answers}
    request = urlrequest.Request(suggestion_url, data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=50) as response:
            suggestion = json.loads(response.read().decode("utf-8"))
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(503, "专属建议暂时没有写好，请稍后再试") from exc
    question_by_id = {str(item.get("id", "")): str(item.get("question", "")).strip() for item in trusted_questions}
    answer_by_id = {}
    for item in trusted_answers:
        selected, extra = str(item.get("selected", "")).strip(), str(item.get("text", "")).strip()
        answer_by_id[str(item.get("question_id", ""))] = "；".join(value for value in (selected, extra) if value)
    def enrich_sources(source_key: str, suggestion_key: str) -> list[list[dict[str, str]]]:
        source_rows = suggestion.get(source_key, []) if isinstance(suggestion.get(source_key), list) else []
        suggestions = suggestion.get(suggestion_key, []) if isinstance(suggestion.get(suggestion_key), list) else []
        enriched = []
        for index in range(len(suggestions)):
            refs = source_rows[index] if index < len(source_rows) and isinstance(source_rows[index], list) else []
            enriched.append([{"question": question_by_id[ref], "answer": answer_by_id[ref]} for ref in refs if ref in question_by_id and answer_by_id.get(ref) and answer_by_id[ref] != "没注意过"])
        return enriched
    suggestion["family_parent_answer_refs"] = enrich_sources("family_suggestion_sources", "family_suggestions")
    suggestion["teacher_parent_answer_refs"] = enrich_sources("teacher_suggestion_sources", "teacher_suggestions")
    if "base_recommendations" not in report:
        report["base_recommendations"] = json.loads(json.dumps(report.get("recommendations", {}), ensure_ascii=False))
    personalized = report.setdefault("personalized_recommendations", {})
    personalized[payload.dimension_key] = suggestion
    report["feedback_completed"] = True
    base = report.get("base_recommendations", {})
    advice_list = lambda value: [str(item).strip() for item in (value if isinstance(value, list) else [value]) if str(item).strip()]
    base_family, base_teacher = advice_list(base.get("family", []))[:4], advice_list(base.get("teacher", []))[:4]
    def auxiliary(kind: str, limit: int) -> list[tuple[str, list[dict[str, str]]]]:
        result, used_sources = [], set()
        for value in personalized.values():
            suggestions = value.get(f"{kind}_suggestions", [])
            sources = value.get(f"{kind}_parent_answer_refs", [])
            for index, text in enumerate(suggestions):
                refs = sources[index] if index < len(sources) else []
                source_key = tuple((ref.get("question", ""), ref.get("answer", "")) for ref in refs)
                if refs and source_key not in used_sources and text not in base_family and text not in base_teacher and all(text != prior[0] for prior in result):
                    result.append((text, refs))
                    used_sources.add(source_key)
                    if len(result) >= limit:
                        return result
        return result
    family_aux, teacher_aux = auxiliary("family", 2), auxiliary("teacher", 1)
    report["recommendations"]["family"] = base_family + [item[0] for item in family_aux]
    report["recommendations"]["teacher"] = base_teacher + [item[0] for item in teacher_aux]
    report["recommendation_attributions"] = {
        "family": [[] for _ in base_family] + [item[1] for item in family_aux],
        "teacher": [[] for _ in base_teacher] + [item[1] for item in teacher_aux],
    }
    timestamp = now_iso()
    with connect() as db:
        db.execute("""INSERT INTO parent_feedback (id,report_id,child_profile_id,author_account_id,dimension_key,questions_json,answers_json,suggestion_json,created_at)
                      VALUES (?,?,?,?,?,?,?,?,?)
                      ON CONFLICT(report_id,author_account_id,dimension_key) DO UPDATE SET questions_json=excluded.questions_json,answers_json=excluded.answers_json,suggestion_json=excluded.suggestion_json,created_at=excluded.created_at""",
                   (str(uuid.uuid4()), report_id, profile["id"], viewer["id"], payload.dimension_key, json.dumps(trusted_questions,ensure_ascii=False), json.dumps(trusted_answers,ensure_ascii=False), json.dumps(suggestion,ensure_ascii=False), timestamp))
        db.execute("UPDATE reports SET report_json=? WHERE id=?", (json.dumps(report,ensure_ascii=False), report_id))
    return {"ok":True,"type":"parent_feedback","suggestion":suggestion,"report":report}


@app.get("/_deprecated/bridge-removed.js", response_class=PlainTextResponse, include_in_schema=False)
def account_bridge() -> PlainTextResponse:
    """供四个独立模块共用的轻量账号与证据桥，不复制登录逻辑。"""
    script = r'''(() => {
  const core = "http://localhost:8020";
  const queuePrefix = "ai-bole-evidence-queue:";
  const queueKey = account => queuePrefix + account.id;
  const readQueue = account => {
    try { return JSON.parse(localStorage.getItem(queueKey(account)) || "[]"); }
    catch (_) { return []; }
  };
  const writeQueue = (account, items) => {
    try { localStorage.setItem(queueKey(account), JSON.stringify(items.slice(-100))); }
    catch (_) {}
  };
  const post = event => fetch(core + "/_deprecated/v0/evidence-events", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event)
  }).then(async response => {
    if (response.ok) return response.json();
    const error = new Error(response.status === 401 ? "account required" : "evidence rejected");
    error.status = response.status;
    throw error;
  });
  const v1Event = event => {
    const raw=event.raw_evidence||{},ctx=event.context||{};
    const type=event.module==="deep_sea"&&event.event_type==="deep_sea_session_completed"?"deep-sea.session-completed.v1":{chat:"chat.observation-shared.v1",story:"story.contribution-completed.v1",deep_sea:"deep-sea.spatial-task-completed.v1",career:"career.task-completed.v1"}[event.module];
    let payload;
    if(event.module==="chat") payload={turnCount:Number(raw.turn_count)||1,topicKey:String(raw.topic||"conversation").slice(0,80)};
    else if(event.module==="story") payload={contributionCount:1,completionSeconds:Number(raw.duration_seconds)||0,storyTitle:String(raw.title||"故事共创").slice(0,120)};
    else if(event.module==="deep_sea"&&type==="deep-sea.session-completed.v1") payload={completedLevels:Math.max(1,Math.min(3,Number(raw.completed_levels)||3)),totalLevels:3,completionSeconds:Number(raw.duration_seconds)||0,adjustmentCount:Number(raw.meaningful_adjustments)||0};
    else if(event.module==="deep_sea") payload={level:Math.max(1,Math.min(3,Number(ctx.level)||1)),completionSeconds:Number(raw.duration_seconds)||0,adjustmentCount:Number(raw.meaningful_adjustments||raw.rotate_count)||0};
    else payload={taskKey:String(raw.career_name||ctx.career_id||"career-task").slice(0,80),attemptCount:Number(raw.interaction_count)||0,hintCount:Number(raw.hint_count)||0,completionSeconds:Number(raw.duration_seconds)||0,adjustmentCount:Number(raw.adjustment_count||raw.retry_count)||0};
    return {schemaVersion:"1.0",eventId:crypto.randomUUID?crypto.randomUUID():Date.now()+":"+Math.random(),idempotencyKey:String(ctx.idempotency_key||Date.now()),eventType:type,occurredAt:event.occurred_at||new Date().toISOString(),payload};
  };
  let v1Sdk=null,v1Ready=null;
  const activateV1=async()=>{if(!window.AIBoleModuleSDK)return null;try{const sdk=window.AIBoleModuleSDK.create({coreUrl:core});await sdk.initialize();await sdk.exchangeLaunchCode();sdk.interruptOnPageHide();v1Sdk=sdk;return sdk}catch(_){return null}};
  const isTerminalEvent=event=>event.module!=="deep_sea"||event.event_type==="deep_sea_session_completed";
  const publishTerminalArtifact=async(event,sdk)=>{
    if(!isTerminalEvent(event))return;
    const raw=event.raw_evidence||{},ctx=event.context||{};
    const type={story:"story",chat:"conversation",deep_sea:"game-result",career:"other"}[event.module];
    const key=String(ctx.idempotency_key||Date.now());
    await sdk.publishArtifact({schemaVersion:"1.0",artifactId:"legacy-adapter:"+key,type,title:String(raw.title||"一次探索作品").slice(0,160),summary:String(event.behavior_summary||"").slice(0,500),previewResourceId:ctx.snapshot_url||null,sourceResourceId:"legacy:"+event.module+":"+key,createdAt:event.occurred_at||new Date().toISOString()});
  };
  const api = {
    account: null,
    ready: fetch(core + "/api/account/me", { credentials: "include" })
      .then(r => r.ok ? r.json() : Promise.reject()).then(v => {
        api.account = v.account;
        v1Ready=activateV1();
        window.dispatchEvent(new CustomEvent("ai-bole-account-ready", { detail: v.account }));
        queueMicrotask(() => api.flushEvidence());
        return v.account;
      }).catch(() => null),
    async captureMoment(selector) {
      try {
        if (!window.html2canvas) {
          await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = core + "/sdk/html2canvas.min.js";
            script.onload = resolve; script.onerror = reject; document.head.appendChild(script);
          });
        }
        const target = document.querySelector(selector || "main") || document.body;
        const canvas = await window.html2canvas(target, { scale: 0.9, useCORS: true, backgroundColor: null, logging: false });
        const response = await fetch(core + "/api/evidence/snapshots", {
          method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data_url: canvas.toDataURL("image/jpeg", 0.76) })
        });
        return response.ok ? (await response.json()).url : null;
      } catch (_) { return null; }
    },
    async emitEvidence(event) {
      if (event.capture_selector) {
        const snapshot = await api.captureMoment(event.capture_selector);
        event.context = Object.assign({}, event.context || {}, snapshot ? { snapshot_url: snapshot } : {});
        delete event.capture_selector;
      }
      const account = api.account || await api.ready;
      if (!account) throw new Error("请先登录探索者账号");
      try {
        await (v1Ready||activateV1());
        if(v1Sdk){const result=await v1Sdk.emitEvidence(v1Event(event));await publishTerminalArtifact(event,v1Sdk);if(isTerminalEvent(event))await v1Sdk.completeSession({legacyEventType:event.event_type});window.dispatchEvent(new CustomEvent("ai-bole-evidence-saved",{detail:result}));return result;}
        const result = await post(event);
        window.dispatchEvent(new CustomEvent("ai-bole-evidence-saved", { detail: result }));
        return result;
      } catch (error) {
        if (error && error.status >= 400 && error.status < 500 && error.status !== 401) throw error;
        const key = event && event.context && event.context.idempotency_key;
        const queued = readQueue(account);
        if (!key || !queued.some(item => item?.context?.idempotency_key === key)) queued.push(event);
        writeQueue(account, queued);
        window.dispatchEvent(new CustomEvent("ai-bole-evidence-queued", { detail: { key } }));
        return { ok: true, queued: true };
      }
    },
    async flushEvidence() {
      const account = api.account || await api.ready;
      if (!account) return { flushed: 0, pending: 0 };
      const queued = readQueue(account);
      const pending = [];
      let flushed = 0;
      for (const event of queued) {
        try { await post(event); flushed += 1; }
        catch (_) { pending.push(event); }
      }
      writeQueue(account, pending);
      if (flushed) window.dispatchEvent(new CustomEvent("ai-bole-evidence-flushed", { detail: { flushed, pending: pending.length } }));
      return { flushed, pending: pending.length };
    },
    returnToPlanet() { location.href = "http://localhost:4173/?from=module"; }
  };
  window.addEventListener("online", () => api.flushEvidence());
  window.__deprecatedAIBole = api;
})();'''
    return PlainTextResponse(script, media_type="application/javascript; charset=utf-8")


class SnapshotIn(BaseModel):
    data_url: str = Field(alias="dataUrl")
    model_config = ConfigDict(populate_by_name=True)


@app.get("/sdk/html2canvas.min.js")
def screenshot_library() -> FileResponse:
    return FileResponse(ROOT / "static" / "html2canvas.min.js", media_type="application/javascript")


@app.get("/sdk/module-sdk.js")
def module_sdk_library() -> FileResponse:
    return FileResponse(REPO_ROOT / "packages" / "module-sdk" / "module-sdk.js", media_type="application/javascript")


@app.post("/api/v1/assets/snapshots", status_code=201)
def create_snapshot(payload: SnapshotIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if "artifact:write" not in json.loads(auth["scopes_json"]): raise HTTPException(403, "模块授权不含作品写入权限")
    prefix = "data:image/jpeg;base64,"
    if not payload.data_url.startswith(prefix):
        raise HTTPException(400, "只支持 JPEG 体验快照")
    try:
        content = base64.b64decode(payload.data_url[len(prefix):], validate=True)
    except ValueError as exc:
        raise HTTPException(400, "体验快照格式无效") from exc
    if len(content) > 2_500_000:
        raise HTTPException(413, "体验快照过大")
    snapshot_id = uuid.uuid4().hex
    (SNAPSHOT_DIR / f"{snapshot_id}.jpg").write_bytes(content)
    with connect() as db:
        db.execute(
            "INSERT INTO snapshot_assets (id,session_id,created_at) VALUES (?,?,?)",
            (snapshot_id, auth["session_id"], now_iso()),
        )
    return {"id": snapshot_id, "url": f"http://localhost:8020/api/v1/assets/snapshots/{snapshot_id}"}


@app.get("/api/v1/assets/snapshots/{snapshot_id}")
def read_snapshot(snapshot_id: str, ai_bole_session: str | None = Cookie(default=None)) -> FileResponse:
    if not snapshot_id.isalnum() or len(snapshot_id) != 32:
        raise HTTPException(404)
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        visible = db.execute(
            """SELECT 1 FROM snapshot_assets sa JOIN assessment_sessions s ON s.id=sa.session_id
               WHERE sa.id=? AND s.child_profile_id=?""",
            (snapshot_id, profile["id"]),
        ).fetchone()
    if not visible:
        raise HTTPException(404)
    path = SNAPSHOT_DIR / f"{snapshot_id}.jpg"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


def issue_session(db: sqlite3.Connection, account_id: str, response: Response, timestamp: str) -> None:
    db.execute("DELETE FROM account_sessions WHERE expires_at<=?", (timestamp,))
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    first_student = db.execute(
        "SELECT student_account_id FROM adult_student_links WHERE adult_account_id=? ORDER BY created_at LIMIT 1",
        (account_id,),
    ).fetchone()
    db.execute(
        """INSERT INTO account_sessions
           (id, account_id, token_hash, expires_at, created_at, selected_student_id)
           VALUES (?,?,?,?,?,?)""",
        (str(uuid.uuid4()), account_id, token_digest(token), expires, timestamp,
         first_student["student_account_id"] if first_student else None),
    )
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=False,
        max_age=SESSION_DAYS * 86400, path="/",
    )


def generate_username(db: sqlite3.Connection, role: str) -> str:
    prefix = ("S" if role == "student" else "A") + datetime.now(timezone.utc).strftime("%Y")
    rows = db.execute(
        "SELECT username FROM accounts WHERE username LIKE ?", (f"{prefix.lower()}%",)
    ).fetchall()
    used = {
        int(suffix)
        for row in rows
        if (suffix := row["username"][len(prefix):]).isdigit()
    }
    number = next(value for value in range(1, 10_000) if value not in used)
    return f"{prefix}{number:04d}".lower()


def account_session_payload(viewer: sqlite3.Row, token: str | None = None) -> dict:
    result = {"account": public_account(viewer)}
    if (viewer["role"] or "student") != "adult":
        result["selected_student"] = public_account(viewer)
        result["students"] = []
        return result
    with connect() as db:
        students = linked_students(db, viewer["id"])
        session = db.execute(
            "SELECT selected_student_id FROM account_sessions WHERE token_hash=?",
            (token_digest(token or ""),),
        ).fetchone()
    selected_id = session["selected_student_id"] if session else None
    selected = next((student for student in students if student["id"] == selected_id), students[0] if students else None)
    result["students"] = [public_account(student) for student in students]
    result["selected_student"] = public_account(selected) if selected else None
    return result


@app.post("/api/account/register", status_code=201)
def register_account(payload: AccountRegistrationIn, response: Response) -> dict:
    timestamp = now_iso()
    with connect() as db:
        username = canonical_generated_username(payload.username) if payload.username else generate_username(db, payload.role)
        if db.execute("SELECT 1 FROM accounts WHERE username=?", (username,)).fetchone():
            raise HTTPException(409, "这个探索者账号已经存在，请直接登录")
        account_id = str(uuid.uuid4())
        salt = secrets.token_hex(16)
        try:
            db.execute(
                """INSERT INTO accounts
                   (id,username,display_name,age,password_hash,password_salt,created_at,updated_at,
                    role,adult_kind)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (account_id, username, payload.display_name, payload.age or 0,
                 password_digest(payload.password, salt), salt, timestamp, timestamp,
                 payload.role, payload.adult_kind),
            )
            if payload.role == "student":
                db.execute(
                    "INSERT INTO child_profiles (id,account_id,display_name,age,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                    (account_id, account_id, payload.display_name, payload.age, timestamp, timestamp),
                )
        except sqlite3.IntegrityError as cause:
            raise HTTPException(409, "这个探索者账号已经存在，请直接登录") from cause
        issue_session(db, account_id, response, timestamp)
        account = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return {"account": public_account(account), "created": True, "generated_username": payload.username is None}


@app.post("/api/account/session")
def create_session(payload: AccountCredentialsIn, response: Response) -> dict:
    timestamp = now_iso()
    with connect() as db:
        account = find_account_by_username(db, payload.username)
        if not account:
            raise HTTPException(401, "账号或密码不正确")
        candidate = password_digest(payload.password, account["password_salt"])
        if not hmac.compare_digest(candidate, account["password_hash"]):
            raise HTTPException(401, "账号或密码不正确")
        if payload.expected_role and (account["role"] or "student") != payload.expected_role:
            label = "学生端" if (account["role"] or "student") == "student" else "老师/家长端"
            raise HTTPException(403, f"这个账号属于{label}，请切换到对应入口登录")
        db.execute("UPDATE accounts SET updated_at=? WHERE id=?", (timestamp, account["id"]))
        issue_session(db, account["id"], response, timestamp)
    return {**account_session_payload(account), "created": False}


@app.post("/api/account/password/reset")
def reset_password(
    payload: PasswordResetIn,
    ai_bole_session: str | None = Cookie(default=None),
) -> dict:
    # 必须已登录：密码重置是敏感操作，绝不允许仅凭用户名任意重置他人密码。
    # 学生忘记密码应联系家长/教师走账号后台流程，或在已登录态下通过此接口改密。
    viewer = require_account(ai_bole_session)
    viewer_username = str(viewer["username"] or "")
    if viewer_username != payload.username.strip().lower():
        raise HTTPException(403, "只能修改当前登录账号的密码")
    with connect() as db:
        account = find_account_by_username(db, payload.username)
        if not account or account["id"] != viewer["id"]:
            raise HTTPException(403, "只能修改当前登录账号的密码")
        salt = secrets.token_hex(16)
        db.execute(
            "UPDATE accounts SET password_hash=?,password_salt=?,updated_at=? WHERE id=?",
            (password_digest(payload.new_password, salt), salt, now_iso(), account["id"]),
        )
        db.execute("DELETE FROM account_sessions WHERE account_id=?", (account["id"],))
    return {"ok": True, "username": account["username"]}


@app.get("/api/account/me")
def account_me(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    return account_session_payload(require_account(ai_bole_session), ai_bole_session)


@app.patch("/api/account/profile")
def update_student_identity(payload: StudentIdentityIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    timestamp = now_iso()
    with connect() as db:
        db.execute("UPDATE accounts SET display_name=?,avatar_id=?,updated_at=? WHERE id=?", (payload.display_name, payload.avatar_id, timestamp, account["id"]))
        db.execute("UPDATE child_profiles SET display_name=?,updated_at=? WHERE account_id=?", (payload.display_name, timestamp, account["id"]))
        updated = db.execute("SELECT * FROM accounts WHERE id=?", (account["id"],)).fetchone()
    return account_session_payload(viewer, ai_bole_session)


@app.get("/api/account/students")
def get_linked_students(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "只有老师/家长账号可以管理学生")
    return account_session_payload(viewer, ai_bole_session)


@app.post("/api/account/students/bind", status_code=201)
def bind_student(payload: StudentLinkIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "只有老师/家长账号可以绑定学生")
    with connect() as db:
        count = db.execute(
            "SELECT COUNT(*) AS total FROM adult_student_links WHERE adult_account_id=?", (viewer["id"],)
        ).fetchone()["total"]
        student = find_account_by_username(db, payload.username)
        if not student or (student["role"] or "student") != "student":
            raise HTTPException(404, "没有找到这个学生账号，请核对后再试")
        exists = db.execute(
            "SELECT 1 FROM adult_student_links WHERE adult_account_id=? AND student_account_id=?",
            (viewer["id"], student["id"]),
        ).fetchone()
        if exists:
            raise HTTPException(409, "这位学生已经绑定")
        if count >= 5:
            raise HTTPException(409, "每个老师/家长账号最多绑定 5 位学生")
        db.execute(
            "INSERT INTO adult_student_links VALUES (?,?,?)", (viewer["id"], student["id"], now_iso())
        )
        db.execute(
            """UPDATE account_sessions SET selected_student_id=COALESCE(selected_student_id, ?)
               WHERE account_id=?""",
            (student["id"], viewer["id"]),
        )
    return {"ok": True, "student": public_account(student), **account_session_payload(viewer, ai_bole_session)}


@app.delete("/api/account/students/{student_id}")
def unbind_student(student_id: str, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "只有老师/家长账号可以解绑学生")
    with connect() as db:
        removed = db.execute(
            "DELETE FROM adult_student_links WHERE adult_account_id=? AND student_account_id=?",
            (viewer["id"], student_id),
        ).rowcount
        next_student = db.execute(
            "SELECT student_account_id FROM adult_student_links WHERE adult_account_id=? ORDER BY created_at LIMIT 1",
            (viewer["id"],),
        ).fetchone()
        db.execute(
            "UPDATE account_sessions SET selected_student_id=? WHERE account_id=? AND selected_student_id=?",
            (next_student["student_account_id"] if next_student else None, viewer["id"], student_id),
        )
    if not removed:
        raise HTTPException(404, "没有找到这条学生绑定")
    return {"ok": True, **account_session_payload(viewer, ai_bole_session)}


@app.post("/api/account/context")
def select_student(payload: StudentContextIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "学生账号无需切换查看对象")
    with connect() as db:
        student = db.execute(
            """SELECT s.* FROM adult_student_links l JOIN accounts s ON s.id=l.student_account_id
               WHERE l.adult_account_id=? AND l.student_account_id=?""",
            (viewer["id"], payload.student_id),
        ).fetchone()
        if not student:
            raise HTTPException(403, "只能查看已经绑定的学生")
        db.execute(
            "UPDATE account_sessions SET selected_student_id=? WHERE token_hash=?",
            (student["id"], token_digest(ai_bole_session or "")),
        )
    return {"ok": True, "selected_student": public_account(student)}


@app.delete("/api/account/session")
def delete_session(response: Response, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    if ai_bole_session:
        with connect() as db:
            account = require_account(ai_bole_session)
            db.execute("UPDATE module_authorizations SET revoked_at=? WHERE session_id IN (SELECT s.id FROM assessment_sessions s JOIN child_profiles p ON p.id=s.child_profile_id WHERE p.account_id=?) AND revoked_at=''", (now_iso(), account["id"]))
            db.execute("DELETE FROM account_sessions WHERE token_hash=?", (token_digest(ai_bole_session),))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/_deprecated/v0/evidence-events", include_in_schema=False)
def create_evidence(payload: DeprecatedEvidenceIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    raise HTTPException(404, "V0 证据接口已移除")
    account = require_account(ai_bole_session)
    event_id = str(uuid.uuid4())
    idempotency_key = payload.context.get("idempotency_key")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        idempotency_key = None
    else:
        idempotency_key = idempotency_key.strip()[:160]
    with connect() as db:
        try:
            db.execute(
                """INSERT INTO evidence_events (
                     id, account_id, module, event_type, occurred_at, evidence_level,
                     intelligence_candidates, behavior_summary, raw_evidence, context,
                     idempotency_key, created_at
                   ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id, account["id"], payload.module, payload.event_type, payload.occurred_at,
                    payload.evidence_level, json.dumps(payload.intelligence_candidates, ensure_ascii=False),
                    payload.behavior_summary, json.dumps(payload.raw_evidence, ensure_ascii=False),
                    json.dumps(payload.context, ensure_ascii=False), idempotency_key, now_iso(),
                ),
            )
            mirrored_v1 = try_mirror_legacy_event_v1(db, account["id"], event_id, payload, idempotency_key)
        except sqlite3.IntegrityError:
            if not idempotency_key:
                raise
            existing = db.execute(
                "SELECT id FROM evidence_events WHERE account_id=? AND idempotency_key=?",
                (account["id"], idempotency_key),
            ).fetchone()
            if not existing:
                raise
            return {"ok": True, "event_id": existing["id"], "duplicate": True}
    return {"ok": True, "event_id": event_id, "duplicate": False, "mirrored_v1": mirrored_v1}


@app.get("/_deprecated/v0/evidence-events", include_in_schema=False)
def list_evidence(ai_bole_session: str | None = Cookie(default=None), limit: int = 200) -> dict:
    raise HTTPException(404, "V0 证据接口已移除")
    account = require_account(ai_bole_session)
    safe_limit = max(1, min(limit, 500))
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM evidence_events WHERE account_id=? ORDER BY occurred_at DESC LIMIT ?",
            (account["id"], safe_limit),
        ).fetchall()
    events = []
    for row in rows:
        events.append({
            "id": row["id"], "module": row["module"], "event_type": row["event_type"],
            "occurred_at": row["occurred_at"], "evidence_level": row["evidence_level"],
            "intelligence_candidates": json.loads(row["intelligence_candidates"]),
            "behavior_summary": row["behavior_summary"], "raw_evidence": json.loads(row["raw_evidence"]),
            "context": json.loads(row["context"]),
        })
    return {"account": public_account(account), "viewer": public_account(viewer), "events": events}


@app.get("/_deprecated/v0/explorer-collection", include_in_schema=False)
def explorer_collection(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    raise HTTPException(404, "V0 聚合接口已移除")
    """分别提供模块高光与账号使用历程，避免两个页面职责重复。"""
    account = require_account(ai_bole_session)
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM evidence_events WHERE account_id=? ORDER BY occurred_at DESC",
            (account["id"],),
        ).fetchall()
    events = [
        {
            "id": row["id"],
            "module": row["module"],
            "event_type": row["event_type"],
            "occurred_at": row["occurred_at"],
            "evidence_level": row["evidence_level"],
            "behavior_summary": row["behavior_summary"],
            "raw_evidence": json.loads(row["raw_evidence"]),
            "context": json.loads(row["context"]),
        }
        for row in rows
    ]
    with connect() as db:
        comments = db.execute(
            """SELECT c.*,a.display_name AS author_name,a.adult_kind AS author_kind
               FROM work_comments c JOIN accounts a ON a.id=c.author_account_id
               WHERE c.student_account_id=? ORDER BY c.created_at""",
            (account["id"],),
        ).fetchall()
        manual_works = db.execute(
            "SELECT * FROM manual_works WHERE student_account_id=? ORDER BY created_at DESC",
            (account["id"],),
        ).fetchall()
    result = build_explorer_collection(public_account(account), events)
    result["works"].extend(manual_work_item(work) for work in manual_works)
    by_work: dict[str, list[dict]] = {}
    for comment in comments:
        by_work.setdefault(comment["work_id"], []).append({
            "id": comment["id"],
            "body": comment["body"],
            "author_name": comment["author_name"],
            "author_kind": comment["author_kind"],
            "created_at": comment["created_at"],
        })
    for work in result["works"]:
        work["comments"] = by_work.get(work["id"], [])
    result["viewer"] = public_account(viewer)
    return result


def manual_work_summary(row: sqlite3.Row) -> str:
    text = " ".join((row["description"] or "").split())
    if not text:
        return "这是我自己添加的作品。"
    return text if len(text) <= 180 else f"{text[:179].rstrip()}…"


MANUAL_WORK_TYPES: dict[str, dict[str, str]] = {
    "story": {
        "full_story": "完整故事", "story_fragment": "故事片段",
        "character_profile": "角色设定", "story_illustration": "故事插画", "other": "其他创作",
    },
    "deep_sea": {
        "base_design": "基地设计", "mission_record": "闯关记录",
        "solution_sketch": "方案草图", "observation_note": "观察笔记", "other": "其他创作",
    },
    "career": {
        "career_card": "职业体验卡", "mission_plan": "任务方案",
        "role_diary": "角色日记", "career_research": "职业小调查", "other": "其他创作",
    },
    "chat": {
        "mood_note": "心情小记", "opinion": "观点表达",
        "conversation_inspiration": "聊天启发", "life_observation": "生活观察", "other": "其他创作",
    },
}


def manual_work_type_key(row: sqlite3.Row) -> str:
    if row["work_type"]:
        return row["work_type"]
    if row["module"] == "story" and str(row["source_id"] or "").startswith("story:"):
        return "full_story"
    return "other"


def manual_work_type_label(row: sqlite3.Row) -> str:
    work_type = manual_work_type_key(row)
    return MANUAL_WORK_TYPES.get(row["module"], {}).get(work_type, "其他创作")


def manual_work_item(row: sqlite3.Row) -> dict:
    return {
        "id": f"manual-{row['id']}",
        "module": row["module"],
        "source_id": row["source_id"],
        "title": row["title"],
        "summary": manual_work_summary(row),
        "detail": row["description"] or "这件作品由我自己添加到作品册。",
        "quote": "",
        "occurred_at": row["created_at"],
        "status": manual_work_type_label(row),
        "unlocked": True,
        "event_type": "manual_work_added",
        "kind": "manual_work",
        "is_highlight": False,
        "snapshot_url": "",
        "metric_label": "作品类型",
        "metric_value": manual_work_type_label(row),
        "usage_count": 1,
    }


@app.post("/api/explorer/works", status_code=201)
def create_manual_work(payload: ManualWorkIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    student = require_student_viewer(ai_bole_session)
    allowed_types = MANUAL_WORK_TYPES[payload.module]
    work_type = payload.work_type or "other"
    if work_type not in allowed_types:
        raise HTTPException(422, "请选择与所属大陆匹配的作品类型")
    created_at = now_iso()
    with connect() as db:
        existing = None
        if payload.source_id:
            existing = db.execute(
                """SELECT * FROM manual_works
                   WHERE student_account_id=? AND module=? AND source_id=?""",
                (student["id"], payload.module, payload.source_id),
            ).fetchone()
        if existing:
            work_id = existing["id"]
            db.execute(
                "UPDATE manual_works SET work_type=?, title=?, description=? WHERE id=?",
                (work_type, payload.title, payload.description, work_id),
            )
        else:
            work_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO manual_works
                   (id,student_account_id,module,work_type,title,description,source_id,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    work_id, student["id"], payload.module, work_type, payload.title,
                    payload.description, payload.source_id, created_at,
                ),
            )
        row = db.execute("SELECT * FROM manual_works WHERE id=?", (work_id,)).fetchone()
    return {
        "work": {**manual_work_item(row), "comments": []},
        "created": existing is None,
        "updated": existing is not None,
    }


@app.delete("/api/explorer/works/{work_id}")
def delete_manual_work(work_id: str, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    student = require_student_viewer(ai_bole_session)
    raw_id = work_id.removeprefix("manual-")
    with connect() as db:
        removed = db.execute(
            "DELETE FROM manual_works WHERE id=? AND student_account_id=?",
            (raw_id, student["id"]),
        ).rowcount
        if removed:
            db.execute(
                "DELETE FROM work_comments WHERE student_account_id=? AND work_id=?",
                (student["id"], f"manual-{raw_id}"),
            )
    if not removed:
        raise HTTPException(404, "没有找到这件自主添加的作品")
    return {"ok": True}


@app.post("/api/explorer/comments", status_code=201)
def create_work_comment(payload: WorkCommentIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    if (viewer["role"] or "student") != "adult":
        raise HTTPException(403, "只有老师/家长可以发表点评")
    student = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, student["id"])
        valid_work_ids = {
            row["id"] for row in db.execute(
                """SELECT a.id FROM artifacts a JOIN assessment_sessions s ON s.id=a.session_id
                   WHERE s.child_profile_id=?""",
                (profile["id"],),
            ).fetchall()
        }
        valid_work_ids.update(
            f"manual-{row['id']}" for row in db.execute(
                "SELECT id FROM manual_works WHERE student_account_id=?", (student["id"],)
            ).fetchall()
        )
        if payload.work_id not in valid_work_ids:
            raise HTTPException(404, "没有找到这件作品")
        comment_id = str(uuid.uuid4())
        created_at = now_iso()
        db.execute(
            "INSERT INTO work_comments VALUES (?,?,?,?,?,?)",
            (comment_id, student["id"], payload.work_id, viewer["id"], payload.body, created_at),
        )
    return {"comment": {
        "id": comment_id, "body": payload.body, "author_name": viewer["display_name"],
        "author_kind": viewer["adult_kind"], "created_at": created_at,
    }}


@app.get("/_deprecated/v0/explorer-talents", include_in_schema=False)
def explorer_talents(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    raise HTTPException(404, "V0 天赋接口已移除")
    """返回六颗星的真实证据计数与收下资格，资格本身不持久化。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        rows = db.execute(
            """SELECT id,module,intelligence_candidates,evidence_level
               FROM evidence_events WHERE account_id=?
               ORDER BY occurred_at ASC, created_at ASC""",
            (account["id"],),
        ).fetchall()
    return {"account_id": account["id"], "talents": build_talent_eligibility(rows)}


@app.get("/_deprecated/v0/evidence-summary", include_in_schema=False)
def evidence_summary(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    raise HTTPException(404, "V0 汇总接口已移除")
    """只统计频次和行为类型，不输出能力分数。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        rows = db.execute(
            "SELECT intelligence_candidates,evidence_level,event_type,module FROM evidence_events WHERE account_id=?",
            (account["id"],),
        ).fetchall()
    summary = {key: {"strong": 0, "reference": 0, "types": set(), "modules": set()} for key in INTELLIGENCES}
    for row in rows:
        for key in json.loads(row["intelligence_candidates"]):
            item = summary[key]
            item[row["evidence_level"]] += 1
            item["types"].add(row["event_type"])
            item["modules"].add(row["module"])
    return {
        "account": public_account(account),
        "rule": "频次与类型仅用于相对强弱判断，禁止直接换算分数或排名。",
        "summary": {key: {**value, "types": sorted(value["types"]), "modules": sorted(value["modules"])} for key, value in summary.items()},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8020, reload=True)
