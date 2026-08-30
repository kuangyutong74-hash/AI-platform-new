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

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from explorer_collection import build_explorer_collection


ROOT = Path(__file__).resolve().parent
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
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1):\d+",
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
              idempotency_key TEXT,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON account_sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_time ON evidence_events(account_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_account_module ON evidence_events(account_id, module);
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
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_adult_links_student ON adult_student_links(student_account_id);
            CREATE INDEX IF NOT EXISTS idx_work_comments_student_work ON work_comments(student_account_id, work_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_manual_works_student_time ON manual_works(student_account_id, created_at DESC);
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
    description: str = Field(default="", max_length=1000)

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
    require_student_viewer(ai_bole_session)
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
        username = payload.username or generate_username(db, payload.role)
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
        except sqlite3.IntegrityError as cause:
            raise HTTPException(409, "这个探索者账号已经存在，请直接登录") from cause
        issue_session(db, account_id, response, timestamp)
        account = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return {"account": public_account(account), "created": True, "generated_username": payload.username is None}


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
        if payload.expected_role and (account["role"] or "student") != payload.expected_role:
            label = "学生端" if (account["role"] or "student") == "student" else "老师/家长端"
            raise HTTPException(403, f"这个账号属于{label}，请切换到对应入口登录")
        db.execute("UPDATE accounts SET updated_at=? WHERE id=?", (timestamp, account["id"]))
        issue_session(db, account["id"], response, timestamp)
    return {**account_session_payload(account), "created": False}


@app.post("/api/account/password/reset")
def reset_password(payload: PasswordResetIn) -> dict:
    with connect() as db:
        account = db.execute("SELECT * FROM accounts WHERE username=?", (payload.username,)).fetchone()
        if not account:
            raise HTTPException(404, "没有找到这个账号，请核对用户名")
        salt = secrets.token_hex(16)
        db.execute(
            "UPDATE accounts SET password_hash=?,password_salt=?,updated_at=? WHERE id=?",
            (password_digest(payload.new_password, salt), salt, now_iso(), account["id"]),
        )
        db.execute("DELETE FROM account_sessions WHERE account_id=?", (account["id"],))
    return {"ok": True}


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
        student = db.execute("SELECT * FROM accounts WHERE username=?", (payload.username,)).fetchone()
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
            db.execute("DELETE FROM account_sessions WHERE token_hash=?", (token_digest(ai_bole_session),))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.post("/api/evidence/events")
def create_evidence(payload: EvidenceIn, ai_bole_session: str | None = Cookie(default=None)) -> dict:
    account = require_student_viewer(ai_bole_session)
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
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
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


@app.get("/api/explorer/collection")
def explorer_collection(ai_bole_session: str | None = Cookie(default=None)) -> dict:
    """提供全部完成作品、模块高光、点评与账号使用历程。"""
    viewer = require_account(ai_bole_session)
    account = resolve_subject(viewer, ai_bole_session)
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


def manual_work_item(row: sqlite3.Row) -> dict:
    return {
        "id": f"manual-{row['id']}",
        "module": row["module"],
        "title": row["title"],
        "summary": "这是我自己添加的作品。",
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
    work_id = str(uuid.uuid4())
    created_at = now_iso()
    with connect() as db:
        db.execute(
            "INSERT INTO manual_works (id,student_account_id,module,title,description,created_at) VALUES (?,?,?,?,?,?)",
            (work_id, student["id"], payload.module, payload.title, payload.description, created_at),
        )
        row = db.execute("SELECT * FROM manual_works WHERE id=?", (work_id,)).fetchone()
    return {"work": {**manual_work_item(row), "comments": []}}


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
        rows = db.execute(
            "SELECT * FROM evidence_events WHERE account_id=? ORDER BY occurred_at DESC",
            (student["id"],),
        ).fetchall()
        events = [{
            "id": row["id"], "module": row["module"], "event_type": row["event_type"],
            "occurred_at": row["occurred_at"], "evidence_level": row["evidence_level"],
            "behavior_summary": row["behavior_summary"],
            "raw_evidence": json.loads(row["raw_evidence"]), "context": json.loads(row["context"]),
        } for row in rows]
        valid_work_ids = {
            work["id"] for work in build_explorer_collection(public_account(student), events)["works"]
        }
        valid_work_ids.update(
            f"manual-{row['id']}"
            for row in db.execute(
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


@app.get("/api/explorer/talents")
def explorer_talents(ai_bole_session: str | None = Cookie(default=None)) -> dict:
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


@app.get("/api/evidence/summary")
def evidence_summary(ai_bole_session: str | None = Cookie(default=None)) -> dict:
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
