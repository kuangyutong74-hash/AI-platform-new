from __future__ import annotations

import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import Cookie, Header, HTTPException, status

from app.config import settings


def _fetch_platform_identity(session_token: str) -> str | None:
    request = Request(
        f"{settings.core_internal_url.rstrip('/')}/api/account/me",
        headers={
            "Cookie": f"ai_bole_session={session_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None

    identity = payload.get("selected_student") or payload.get("account")
    student_id = identity.get("id") if isinstance(identity, dict) else None
    if not isinstance(identity, dict) or identity.get("role", "student") != "student":
        return None
    return student_id.strip() if isinstance(student_id, str) and student_id.strip() else None


def _fetch_module_identity(authorization: str) -> str | None:
    request = Request(
        f"{settings.core_internal_url.rstrip('/')}/api/v1/module-authorizations:identity",
        headers={"Authorization": authorization, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    if payload.get("moduleId") != "story":
        return None
    student_id = payload.get("studentId")
    return student_id.strip() if isinstance(student_id, str) and student_id.strip() else None


async def require_platform_student_id(
    ai_bole_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    if authorization and authorization.startswith("Bearer "):
        student_id = await asyncio.to_thread(_fetch_module_identity, authorization)
        if student_id:
            return student_id
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="模块授权已失效，请返回探索星球重新进入")
    if not ai_bole_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录平台账号")
    student_id = await asyncio.to_thread(_fetch_platform_identity, ai_bole_session)
    if not student_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    return student_id
