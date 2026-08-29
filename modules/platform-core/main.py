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
import base64
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from urllib import error as urlerror
from urllib import request as urlrequest

from fastapi import Cookie, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from explorer_collection import build_explorer_collection


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
MODULE_CONFIG_DIR = REPO_ROOT / "config" / "modules"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOT_DIR = DATA_DIR / "evidence-snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("AI_BOLE_DB_PATH", DATA_DIR / "ai_bole_core.db")).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
COOKIE_NAME = "ai_bole_session"
SESSION_DAYS = 30

MODULES = {"chat", "story", "deep_sea", "career"}
INTELLIGENCES = {
    "linguistic", "logical_mathematical", "spatial",
    "interpersonal", "intrapersonal", "naturalistic",
}
CANONICAL_INTELLIGENCES = {
    "linguistic", "logical", "spatial",
    "interpersonal", "intrapersonal", "naturalistic",
}
INTELLIGENCE_SYNONYMS = {"logical_mathematical": "logical"}
INTELLIGENCE_NAMES = {
    "linguistic": "语言智能",
    "logical": "逻辑—数学智能",
    "spatial": "空间智能",
    "interpersonal": "人际智能",
    "intrapersonal": "内省智能",
    "naturalistic": "自然观察智能",
}

app = FastAPI(title="AI伯乐平台核心服务", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173", "http://localhost:3000", "http://localhost:5174",
        "http://localhost:3001", "http://localhost:8000", "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 5000")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def load_module_catalog() -> list[dict]:
    """读取版本化模块清单；Portal 只消费该目录，不再维护第二份固定 URL。"""
    catalog: list[dict] = []
    for path in sorted(MODULE_CONFIG_DIR.glob("*.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"模块清单无效：{path.name}") from exc
        required = {"id", "version", "name", "entryUrl", "targetAge", "constructRegistryVersion", "constructs", "supportedEventTypes", "capabilities"}
        if not required.issubset(manifest) or manifest["id"] not in MODULES:
            raise RuntimeError(f"模块清单字段不完整：{path.name}")
        catalog.append(manifest)
    if {item["id"] for item in catalog} != MODULES:
        raise RuntimeError("模块清单必须完整登记 chat、story、deep_sea、career")
    return catalog


def initialize_database() -> None:
    with connect() as db:
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
            CREATE TABLE IF NOT EXISTS evidence_events (
              id TEXT PRIMARY KEY,
              account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
              module TEXT NOT NULL,
              event_type TEXT NOT NULL,
              occurred_at TEXT NOT NULL,
              evidence_level TEXT NOT NULL,
              intelligence_candidates TEXT NOT NULL,
              behavior_summary TEXT NOT NULL,
              raw_evidence TEXT NOT NULL,
              context TEXT NOT NULL,
              idempotency_key TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON account_sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_time ON evidence_events(account_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_module ON evidence_events(account_id, module);
            CREATE TABLE IF NOT EXISTS child_profiles (
              id TEXT PRIMARY KEY,
              account_id TEXT NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
              display_name TEXT NOT NULL,
              age INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
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
            CREATE INDEX IF NOT EXISTS idx_assessment_profile_time ON assessment_sessions(child_profile_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_source_event_session_time ON source_events(session_id, occurred_at DESC);
            """
        )
        evidence_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(evidence_events)").fetchall()
        }
        if "idempotency_key" not in evidence_columns:
            db.execute("ALTER TABLE evidence_events ADD COLUMN idempotency_key TEXT")
        db.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_account_idempotency
               ON evidence_events(account_id, idempotency_key)
               WHERE idempotency_key IS NOT NULL"""
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        db.execute(
            """INSERT OR IGNORE INTO child_profiles (id,account_id,display_name,age,created_at,updated_at)
               SELECT id,id,display_name,age,created_at,updated_at FROM accounts"""
        )
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


initialize_database()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def password_digest(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 180_000).hex()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def public_account(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "age": row["age"],
        "created_at": row["created_at"],
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


def build_talent_eligibility(rows: list[sqlite3.Row]) -> list[dict]:
    """聚合可追溯证据，只判定是否具备收下资格，不换算分数或排名。"""
    aggregates = {
        key: {"strong": 0, "reference": 0, "modules": set(), "recent_id": None}
        for key in CANONICAL_INTELLIGENCES
    }
    for row in rows:
        try:
            candidates = json.loads(row["intelligence_candidates"])
        except (TypeError, json.JSONDecodeError):
            candidates = []
        normalized = {
            INTELLIGENCE_SYNONYMS.get(candidate, candidate)
            for candidate in candidates
            if isinstance(candidate, str)
        } & CANONICAL_INTELLIGENCES
        for key in normalized:
            item = aggregates[key]
            item["modules"].add(row["module"])
            if row["evidence_level"] == "strong":
                item["strong"] += 1
                item["recent_id"] = row["id"]
            else:
                item["reference"] += 1
    return [
        {
            "key": key,
            "name": INTELLIGENCE_NAMES[key],
            "strong_count": values["strong"],
            "reference_count": values["reference"],
            "eligible": values["strong"] >= 1,
            "source_modules": sorted(values["modules"]),
            "recent_evidence_id": values["recent_id"],
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

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return normalize_username(value)


class AccountRegistrationIn(AccountCredentialsIn):
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=4, le=18)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("请填写孩子昵称")
        return value


class EvidenceIn(BaseModel):
    module: str
    event_type: str = Field(min_length=3, max_length=80)
    occurred_at: str = Field(default_factory=now_iso)
    evidence_level: Literal["strong", "reference"]
    intelligence_candidates: list[str] = Field(min_length=1, max_length=3)
    behavior_summary: str = Field(min_length=4, max_length=240)
    raw_evidence: dict = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)

    @field_validator("module")
    @classmethod
    def validate_module(cls, value: str) -> str:
        if value not in MODULES:
            raise ValueError("未知模块")
        return value

    @field_validator("intelligence_candidates")
    @classmethod
    def validate_intelligences(cls, values: list[str]) -> list[str]:
        clean = list(dict.fromkeys(values))
        if any(value not in INTELLIGENCES for value in clean):
            raise ValueError("未知多元智能维度")
        return clean


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


def event_schema_required_fields(event_type: str) -> set[str]:
    schema_path = REPO_ROOT / "packages" / "contracts" / "schemas" / "evidence" / f"{event_type}.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "没有匹配的证据事件契约") from exc
    return set(schema.get("required", []))


def policy_for_event(event_type: str) -> dict:
    policy_path = REPO_ROOT / "config" / "evidence-policy.v1.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    rule = next((item for item in policy["rules"] if item["eventType"] == event_type), None)
    if not rule:
        raise HTTPException(422, "该事件未配置证据策略")
    return {**rule, "policyVersion": policy["version"], "constructRegistryVersion": policy["constructRegistryVersion"]}


def legacy_events_for_report(db: sqlite3.Connection, account_id: str) -> list[dict]:
    rows = db.execute("SELECT * FROM evidence_events WHERE account_id=? ORDER BY occurred_at ASC", (account_id,)).fetchall()
    return [{"id": row["id"], "module": row["module"], "event_type": row["event_type"], "occurred_at": row["occurred_at"], "evidence_level": row["evidence_level"], "intelligence_candidates": json.loads(row["intelligence_candidates"]), "behavior_summary": row["behavior_summary"], "raw_evidence": json.loads(row["raw_evidence"]), "context": json.loads(row["context"])} for row in rows]


def generate_report_snapshot(child_name: str, events: list[dict]) -> dict:
    url = os.environ.get("REPORT_AGENT_URL", "http://localhost:8030/api/report/generate")
    request = urlrequest.Request(url, data=json.dumps({"child_name": child_name, "events": events}, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlrequest.urlopen(request, timeout=50) as response:
            return json.loads(response.read().decode("utf-8"))
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
    account = require_account(ai_bole_session)
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
        db.execute("UPDATE module_authorizations SET exchanged_at=?,token_hash=?,expires_at=? WHERE id=?", (timestamp, token_digest(token), expires, row["id"]))
        if row["status"] == "created":
            db.execute("UPDATE assessment_sessions SET status='active',started_at=?,state_version=state_version+1 WHERE id=?", (timestamp, row["session_id"]))
    return {"token": token, "tokenType": "Bearer", "expiresAt": expires}


@app.patch("/api/v1/assessment-sessions/{session_id}")
def change_assessment_session(session_id: str, payload: SessionStatusIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if auth["session_id"] != session_id:
        raise HTTPException(403, "模块授权不属于该探索会话")
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
        db.execute("UPDATE assessment_sessions SET status=?,ended_at=?,state_version=state_version+1 WHERE id=?", (payload.status, ended_at, session_id))
    return {"id": session_id, "status": payload.status, "duplicate": False}


@app.post("/api/v1/evidence-events:batch")
def create_evidence_events_v1(payload: EvidenceBatchIn, authorization: str | None = Header(default=None)) -> dict:
    auth = require_module_authorization(authorization)
    if auth["status"] not in {"active", "interrupted"}:
        raise HTTPException(409, "探索会话当前不能写入证据")
    manifest = module_manifest(auth["module_id"])
    saved: list[dict] = []
    with connect() as db:
        for event in payload.events:
            if event.event_type not in manifest["supportedEventTypes"]:
                raise HTTPException(422, "该模块版本不支持此事件类型")
            required_fields = event_schema_required_fields(event.event_type)
            if not required_fields.issubset(event.payload):
                raise HTTPException(422, "证据事件缺少必填字段")
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


@app.post("/api/v1/reports")
def create_report_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """报告生成实现仍可独立部署，但证据读取和快照保存只经过 Core。"""
    account = require_account(ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        events = legacy_events_for_report(db, account["id"])
    report = generate_report_snapshot(profile["display_name"], events)
    timestamp = now_iso()
    evidence_hash = hashlib.sha256(json.dumps(events, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    with connect() as db:
        report_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO reports
               (id,child_profile_id,generator_version,ruleset_version,prompt_version,model_id,evidence_set_hash,status,report_json,generated_at,published_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (report_id, profile["id"], "report-agent-v1", "rule-or-llm-v1", None, None, evidence_hash, "published", json.dumps(report, ensure_ascii=False), timestamp, timestamp),
        )
    return {"id": report_id, "status": "published", "report": report}


@app.get("/api/v1/reports/latest-published")
def latest_published_report_v1(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    account = require_account(ai_bole_session)
    with connect() as db:
        profile = profile_for_account(db, account["id"])
        row = db.execute("SELECT * FROM reports WHERE child_profile_id=? AND status='published' ORDER BY published_at DESC LIMIT 1", (profile["id"],)).fetchone()
    if not row:
        raise HTTPException(404, "还没有已发布的报告")
    return {"id": row["id"], "status": row["status"], "generatedAt": row["generated_at"], "report": json.loads(row["report_json"])}


@app.get("/ai-bole-bridge.js", response_class=PlainTextResponse)
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
  const post = event => fetch(core + "/api/evidence/events", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(event)
  }).then(async response => {
    if (response.ok) return response.json();
    const error = new Error(response.status === 401 ? "account required" : "evidence rejected");
    error.status = response.status;
    throw error;
  });
  const api = {
    account: null,
    ready: fetch(core + "/api/account/me", { credentials: "include" })
      .then(r => r.ok ? r.json() : Promise.reject()).then(v => {
        api.account = v.account;
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
  window.AIBole = api;
})();'''
    return PlainTextResponse(script, media_type="application/javascript; charset=utf-8")


class SnapshotIn(BaseModel):
    data_url: str


@app.get("/sdk/html2canvas.min.js")
def screenshot_library() -> FileResponse:
    return FileResponse(ROOT / "static" / "html2canvas.min.js", media_type="application/javascript")


@app.post("/api/evidence/snapshots")
def create_snapshot(payload: SnapshotIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    require_account(ai_bole_session)
    prefix = "data:image/jpeg;base64,"
    if not payload.data_url.startswith(prefix):
        raise HTTPException(400, "只支持 JPEG 体验快照")
    try:
        content = base64.b64decode(payload.data_url[len(prefix):], validate=True)
    except ValueError as exc:
        raise HTTPException(400, "体验快照格式无效") from exc
    if len(content) > 2_500_000:
        raise HTTPException(413, "体验快照过大")
    filename = f"{uuid.uuid4().hex}.jpg"
    (SNAPSHOT_DIR / filename).write_bytes(content)
    return {"url": f"http://localhost:8020/api/evidence/snapshots/{filename}"}


@app.get("/api/evidence/snapshots/{filename}")
def read_snapshot(filename: str) -> FileResponse:
    if not filename.endswith(".jpg") or Path(filename).name != filename:
        raise HTTPException(404)
    path = SNAPSHOT_DIR / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


def issue_session(db: sqlite3.Connection, account_id: str, response: Response, timestamp: str) -> None:
    db.execute("DELETE FROM account_sessions WHERE expires_at<=?", (timestamp,))
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    db.execute(
        "INSERT INTO account_sessions VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), account_id, token_digest(token), expires, timestamp),
    )
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=False,
        max_age=SESSION_DAYS * 86400, path="/",
    )


@app.post("/api/account/register", status_code=201)
def register_account(payload: AccountRegistrationIn, response: Response) -> dict:
    timestamp = now_iso()
    with connect() as db:
        if db.execute("SELECT 1 FROM accounts WHERE username=?", (payload.username,)).fetchone():
            raise HTTPException(409, "这个探索者账号已经存在，请直接登录")
        account_id = str(uuid.uuid4())
        salt = secrets.token_hex(16)
        try:
            db.execute(
                "INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?)",
                (account_id, payload.username, payload.display_name, payload.age,
                 password_digest(payload.password, salt), salt, timestamp, timestamp),
            )
        except sqlite3.IntegrityError as cause:
            raise HTTPException(409, "这个探索者账号已经存在，请直接登录") from cause
        issue_session(db, account_id, response, timestamp)
        account = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return {"account": public_account(account), "created": True}


@app.post("/api/account/session")
def create_session(payload: AccountCredentialsIn, response: Response) -> dict:
    timestamp = now_iso()
    with connect() as db:
        account = db.execute("SELECT * FROM accounts WHERE username=?", (payload.username,)).fetchone()
        if not account:
            raise HTTPException(401, "账号或密码不正确")
        candidate = password_digest(payload.password, account["password_salt"])
        if not hmac.compare_digest(candidate, account["password_hash"]):
            raise HTTPException(401, "账号或密码不正确")
        db.execute("UPDATE accounts SET updated_at=? WHERE id=?", (timestamp, account["id"]))
        issue_session(db, account["id"], response, timestamp)
    return {"account": public_account(account), "created": False}


@app.get("/api/account/me")
def account_me(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    return {"account": public_account(require_account(ai_bole_session))}


@app.delete("/api/account/session")
def delete_session(response: Response, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    if ai_bole_session:
        with connect() as db:
            db.execute("DELETE FROM account_sessions WHERE token_hash=?", (token_digest(ai_bole_session),))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/api/evidence/events")
def create_evidence(payload: EvidenceIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
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
    return {"ok": True, "event_id": event_id, "duplicate": False}


@app.get("/api/evidence/events")
def list_evidence(ai_bole_session: str | None = Cookie(default=None), limit: int = 200) -> dict:
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
    return {"account": public_account(account), "events": events}


@app.get("/api/explorer/collection")
def explorer_collection(ai_bole_session: str | None = Cookie(default=None)) -> dict:
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
    return build_explorer_collection(public_account(account), events)


@app.get("/api/explorer/talents")
def explorer_talents(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """返回六颗星的真实证据计数与收下资格，资格本身不持久化。"""
    account = require_account(ai_bole_session)
    with connect() as db:
        rows = db.execute(
            """SELECT id,module,intelligence_candidates,evidence_level
               FROM evidence_events WHERE account_id=?
               ORDER BY occurred_at ASC, created_at ASC""",
            (account["id"],),
        ).fetchall()
    return {"account_id": account["id"], "talents": build_talent_eligibility(rows)}


@app.get("/api/evidence/summary")
def evidence_summary(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """只统计频次和行为类型，不输出能力分数。"""
    account = require_account(ai_bole_session)
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
