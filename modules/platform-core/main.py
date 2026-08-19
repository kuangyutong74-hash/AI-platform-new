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
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "ai_bole_core.db"
COOKIE_NAME = "ai_bole_session"
SESSION_DAYS = 30

MODULES = {"chat", "story", "deep_sea", "career"}
INTELLIGENCES = {
    "linguistic", "logical_mathematical", "spatial",
    "interpersonal", "intrapersonal", "naturalistic",
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
    return db


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
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON account_sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_time ON evidence_events(account_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_module ON evidence_events(account_id, module);
            """
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
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "age": row["age"]}


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


class AccountSessionIn(BaseModel):
    username: str = Field(min_length=2, max_length=30)
    display_name: str = Field(min_length=1, max_length=30)
    age: int = Field(ge=4, le=18)
    password: str = Field(min_length=4, max_length=72)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not all(ch.isalnum() or ch in "_-" for ch in value):
            raise ValueError("账号只能包含文字、数字、下划线或短横线")
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


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "ai-bole-platform-core"}


@app.get("/ai-bole-bridge.js", response_class=PlainTextResponse)
def account_bridge() -> PlainTextResponse:
    """供四个独立模块共用的轻量账号与证据桥，不复制登录逻辑。"""
    script = r'''(() => {
  const core = "http://localhost:8020";
  const api = {
    account: null,
    ready: fetch(core + "/api/account/me", { credentials: "include" })
      .then(r => r.ok ? r.json() : Promise.reject()).then(v => {
        api.account = v.account;
        window.dispatchEvent(new CustomEvent("ai-bole-account-ready", { detail: v.account }));
        return v.account;
      }).catch(() => null),
    emitEvidence(event) {
      return fetch(core + "/api/evidence/events", {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(event)
      }).then(r => r.ok ? r.json() : Promise.reject(new Error("evidence rejected")));
    },
    returnToPlanet() { location.href = "http://localhost:4173/?from=module"; }
  };
  window.AIBole = api;
})();'''
    return PlainTextResponse(script, media_type="application/javascript; charset=utf-8")


@app.post("/api/account/session")
def create_session(payload: AccountSessionIn, response: Response) -> dict:
    timestamp = now_iso()
    with connect() as db:
        account = db.execute("SELECT * FROM accounts WHERE username=?", (payload.username,)).fetchone()
        if account:
            candidate = password_digest(payload.password, account["password_salt"])
            if not hmac.compare_digest(candidate, account["password_hash"]):
                raise HTTPException(401, "账号或密码不正确")
            db.execute(
                "UPDATE accounts SET display_name=?, age=?, updated_at=? WHERE id=?",
                (payload.display_name.strip(), payload.age, timestamp, account["id"]),
            )
            account_id = account["id"]
        else:
            account_id = str(uuid.uuid4())
            salt = secrets.token_hex(16)
            db.execute(
                "INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?)",
                (account_id, payload.username, payload.display_name.strip(), payload.age,
                 password_digest(payload.password, salt), salt, timestamp, timestamp),
            )

        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
        db.execute(
            "INSERT INTO account_sessions VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), account_id, token_digest(token), expires, timestamp),
        )
        account = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()

    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=False,
        max_age=SESSION_DAYS * 86400, path="/",
    )
    return {"account": public_account(account), "created": account["created_at"] == timestamp}


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
    with connect() as db:
        db.execute(
            "INSERT INTO evidence_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                event_id, account["id"], payload.module, payload.event_type, payload.occurred_at,
                payload.evidence_level, json.dumps(payload.intelligence_candidates, ensure_ascii=False),
                payload.behavior_summary, json.dumps(payload.raw_evidence, ensure_ascii=False),
                json.dumps(payload.context, ensure_ascii=False), now_iso(),
            ),
        )
    return {"ok": True, "event_id": event_id}


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
