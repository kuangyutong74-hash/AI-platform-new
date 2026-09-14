"""Shared DeepSeek configuration for the integrated platform."""

import os
from pathlib import Path


PLATFORM_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = PLATFORM_DIR / ".env"


def _read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _first(values: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = os.getenv(key) or values.get(key)
        if value:
            return value
    return default


def load_deepseek_config() -> tuple[str, str, str]:
    values = _read_env_file()
    api_key = _first(values, "AI_API_KEY", "ZHIPUAI_API_KEY", "ZHIPU_API_KEY", "DEEPSEEK_API_KEY")
    base_url = _first(values, "AI_BASE_URL", "AI_API_BASE", "ZHIPUAI_BASE_URL", "ZHIPU_BASE_URL", "DEEPSEEK_BASE_URL", default="https://api.deepseek.com/v1")
    model = _first(values, "AI_MODEL", "ZHIPUAI_MODEL", "ZHIPU_MODEL", "DEEPSEEK_MODEL", default="deepseek-chat")
    return api_key.strip(), base_url.strip(), model.strip()
