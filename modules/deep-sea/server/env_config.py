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


def load_deepseek_config() -> tuple[str, str, str]:
    values = _read_env_file()
    api_key = os.getenv("DEEPSEEK_API_KEY", values.get("DEEPSEEK_API_KEY", ""))
    base_url = os.getenv("DEEPSEEK_BASE_URL", values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    model = os.getenv("DEEPSEEK_MODEL", values.get("DEEPSEEK_MODEL", "deepseek-chat"))
    return api_key.strip(), base_url.strip(), model.strip()
