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

from reports import generate_internal_report


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
    return catalog


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


def build_talent_eligibility(rows: list[sqlite3.Row]) -> list[dict]:
    """从 V1 evidence record 推导六星资格；至少一条 strong 才能点亮。"""
    aggregates = {
        key: {"strong": 0, "reference": 0, "modules": set(), "recent_id": None}
        for key in CANONICAL_INTELLIGENCES
    }
    dimensions = construct_dimension_map()
    for row in rows:
        try:
            constructs = json.loads(row["constructs_json"])
        except (TypeError, json.JSONDecodeError):
            constructs = []
        normalized = {dimensions[item] for item in constructs if item in dimensions}
        for key in normalized:
            item = aggregates[key]
            item["modules"].add(row["module_id"])
            if row["evidence_level"] == "strong":
                item["strong"] += 1
                item["recent_id"] = row["id"]
            else:
                item["reference"] += 1
    return [
        {
            "key": key,
            "name": INTELLIGENCE_NAMES[key],
            "strongCount": values["strong"],
            "referenceCount": values["reference"],
            "eligible": values["strong"] >= 1,
            "sourceModules": sorted(values["modules"]),
            "recentEvidenceRecordId": values["recent_id"],
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


def standard_events_for_report(db: sqlite3.Connection, profile_id: str) -> tuple[list[dict], list[str]]:
    """将 V1 事件和派生证据投影为报告输入，引用始终使用 evidence record ID。"""
    rows = db.execute(
        """SELECT se.*, er.id AS evidence_id, er.evidence_level, er.constructs_json, er.behavior_summary, s.module_id
           FROM source_events se JOIN evidence_records er ON er.source_event_id=se.id
           JOIN assessment_sessions s ON s.id=se.session_id
           WHERE s.child_profile_id=? ORDER BY se.occurred_at ASC""", (profile_id,)
    ).fetchall()
    dimension_by_construct = construct_dimension_map()
    events = []
    for row in rows:
        constructs = json.loads(row["constructs_json"])
        payload = json.loads(row["payload_json"])
        events.append({"id": row["evidence_id"], "module": row["module_id"], "event_type": row["event_type"], "occurred_at": row["occurred_at"], "evidence_level": row["evidence_level"], "intelligence_candidates": list(dict.fromkeys(dimension_by_construct.get(key) for key in constructs if dimension_by_construct.get(key))), "behavior_summary": row["behavior_summary"], "raw_evidence": payload, "context": {"sourceEventId": row["id"], "constructs": constructs}})
    return events, [row["evidence_id"] for row in rows]


def generate_report_snapshot(child_name: str, events: list[dict]) -> tuple[dict, dict]:
    """默认走 Core 内置规则；配置 REPORT_AGENT_URL 时可保留独立服务作回归对照。"""
    url = os.environ.get("REPORT_AGENT_URL", "").strip()
    if not url:
        return generate_internal_report(child_name, events), {"generatorVersion": "core-rule-analyzer-v1", "rulesetVersion": "core-rules-v1", "promptVersion": None, "modelId": None}
    request = urlrequest.Request(url, data=json.dumps({"child_name": child_name, "events": events}, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=50) as response:
            report = json.loads(response.read().decode("utf-8"))
            return report, {"generatorVersion": "report-agent-http-v1", "rulesetVersion": "rule-or-llm-v1", "promptVersion": None, "modelId": os.environ.get("REPORT_LLM_MODEL") or None}
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(503, "报告生成服务暂不可用") from exc


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "ai-bole-platform-core"}


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
    expires = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        if not manifest["targetAge"]["min"] <= profile["age"] <= manifest["targetAge"]["max"]:
            raise HTTPException(422, "当前年龄不在该体验模块的适用范围")
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
    return {"sessionId": session_id, "moduleId": manifest["id"], "moduleVersion": manifest["version"], "launchCode": launch_code, "launchCodeExpiresAt": expires, "returnUrl": "http://localhost:4173/?from=module", "contractVersion": "1.0"}


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


@app.patch("/api/v1/assessment-sessions/{session_id}")
def change_assessment_session(session_id: str, payload: SessionStatusIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if auth["session_id"] != session_id:
        raise HTTPException(403, "模块授权不属于该探索会话")
    required_scope = "session:complete" if payload.status == "completed" else "session:interrupt"
    if required_scope not in json.loads(auth["scopes_json"]): raise HTTPException(403, "模块授权不含会话状态权限")
    allowed = {"active": {"completed", "interrupted", "abandoned"}, "interrupted": {"active", "abandoned"}}
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


@app.get("/api/v1/artifacts")
def list_artifacts_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = db.execute("""SELECT a.*, s.module_id, s.module_version FROM artifacts a
                           JOIN assessment_sessions s ON s.id=a.session_id
                           WHERE s.child_profile_id=? ORDER BY a.created_at DESC""", (profile["id"],)).fetchall()
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
    manually_collected_sources = {
        (row["module"], row["source_id"])
        for row in manual_rows if row["source_id"]
    }
    artifacts = [{
        "id": row["id"], "sessionId": row["session_id"], "moduleId": row["module_id"],
        "moduleVersion": row["module_version"], "type": row["type"], "kind": "highlight",
        "title": row["title"], "summary": row["summary"], "detail": row["summary"],
        "previewResourceId": row["preview_resource_id"], "sourceResourceId": row["source_resource_id"],
        "createdAt": row["created_at"], "comments": comments.get(row["id"], []),
    } for row in rows if (row["module_id"], row["source_resource_id"]) not in manually_collected_sources]
    artifacts.extend({
        "id": f"manual-{row['id']}", "sessionId": None, "moduleId": row["module"],
        "moduleVersion": None, "type": "manual", "kind": "manual_work", "title": row["title"],
        "summary": manual_work_summary(row), "detail": row["description"] or "这件作品由我自己添加到作品册。",
        "previewResourceId": None, "sourceResourceId": row["source_id"] or None, "createdAt": row["created_at"],
        "comments": comments.get(f"manual-{row['id']}", []),
    } for row in manual_rows)
    artifacts.sort(key=lambda item: item["createdAt"], reverse=True)
    return {"account": public_account(account), "viewer": public_account(viewer), "artifacts": artifacts}


def evidence_rows_for_profile(db: sqlite3.Connection, profile_id: str, limit: int = 500) -> list[sqlite3.Row]:
    return db.execute(
        """SELECT er.id,se.id AS source_event_id,se.session_id,se.event_type,se.payload_json,se.occurred_at,
                  er.evidence_level,er.constructs_json,er.behavior_summary,s.module_id,s.module_version
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
        "constructs": (constructs := json.loads(row["constructs_json"])),
        "reportDimensions": list(dict.fromkeys(dimensions[key] for key in constructs if key in dimensions)),
        "behaviorSummary": row["behavior_summary"], "payload": json.loads(row["payload_json"]),
    } for row in rows]}


@app.get("/api/v1/talents")
def list_talents_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = evidence_rows_for_profile(db, profile["id"], 500)
    return {"rule": "至少存在一条 strong 标准证据时，该维度可以点亮。", "talents": build_talent_eligibility(rows)}


@app.get("/api/v1/timeline")
def timeline_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        rows = db.execute("""SELECT s.id,s.module_id,s.module_version,s.status,s.started_at,s.ended_at,s.active_seconds,
                           (SELECT COUNT(*) FROM source_events e WHERE e.session_id=s.id) AS evidence_count,
                           (SELECT COUNT(*) FROM artifacts a WHERE a.session_id=s.id) AS artifact_count
                           FROM assessment_sessions s
                           WHERE s.child_profile_id=? AND s.status='completed'
                           ORDER BY COALESCE(s.ended_at,s.started_at,s.created_at) DESC""", (profile["id"],)).fetchall()
    sessions = [{"id": row["id"], "moduleId": row["module_id"], "moduleVersion": row["module_version"], "status": row["status"], "startedAt": row["started_at"], "endedAt": row["ended_at"], "activeSeconds": row["active_seconds"], "evidenceCount": row["evidence_count"], "artifactCount": row["artifact_count"]} for row in rows]
    grouped: dict[str, list[dict]] = {}
    for session in sessions:
        grouped.setdefault(session["moduleId"], []).append(session)
    module_summaries = []
    for module_id, items in grouped.items():
        ordered = sorted(items, key=lambda item: item["endedAt"] or item["startedAt"] or "")
        module_summaries.append({"moduleId": module_id, "completedCount": len(items), "firstUsedAt": ordered[0]["startedAt"] or ordered[0]["endedAt"], "lastUsedAt": ordered[-1]["endedAt"] or ordered[-1]["startedAt"], "activeSeconds": sum(item["activeSeconds"] for item in items), "evidenceCount": sum(item["evidenceCount"] for item in items), "artifactCount": sum(item["artifactCount"] for item in items)})
    return {"sessions": sessions, "moduleSummaries": module_summaries}


@app.get("/api/v1/assessment-sessions/{session_id}")
def read_assessment_session(session_id: str, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        row = db.execute("SELECT * FROM assessment_sessions WHERE id=? AND child_profile_id=?", (session_id, profile["id"])).fetchone()
    if not row: raise HTTPException(404, "探索会话不存在")
    return {"id": row["id"], "moduleId": row["module_id"], "moduleVersion": row["module_version"], "status": row["status"], "createdAt": row["created_at"], "startedAt": row["started_at"], "endedAt": row["ended_at"], "activeSeconds": row["active_seconds"], "stateVersion": row["state_version"], "summary": json.loads(row["summary_json"] or "{}"), "reason": row["interruption_reason"]}


@app.post("/api/v1/reports")
def create_report_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """报告生成实现仍可独立部署，但证据读取和快照保存只经过 Core。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        events, evidence_ids = standard_events_for_report(db, profile["id"])
    report, generator = generate_report_snapshot(profile["display_name"], events)
    timestamp = now_iso()
    evidence_hash = hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    with connect() as db:
        report_id = str(uuid.uuid4())
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
    return {"id": row["id"], "status": row["status"], "generatedAt": row["generated_at"], "report": json.loads(row["report_json"])}


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
def reset_password(payload: PasswordResetIn) -> dict:
    with connect() as db:
        account = find_account_by_username(db, payload.username)
        if not account:
            raise HTTPException(404, "没有找到这个账号，请核对用户名")
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
        "status": "我添加的作品",
        "unlocked": True,
        "event_type": "manual_work_added",
        "kind": "manual_work",
        "is_highlight": False,
        "snapshot_url": "",
        "metric_label": "作品来源",
        "metric_value": "自主添加",
        "usage_count": 1,
    }


@app.post("/api/explorer/works", status_code=201)
def create_manual_work(payload: ManualWorkIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    student = require_student_viewer(ai_bole_session)
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
                "UPDATE manual_works SET title=?, description=? WHERE id=?",
                (payload.title, payload.description, work_id),
            )
        else:
            work_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO manual_works
                   (id,student_account_id,module,title,description,source_id,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    work_id, student["id"], payload.module, payload.title,
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
    uvicorn.run("main:app", host="0.0.0.0", port=8020, reload=False)
