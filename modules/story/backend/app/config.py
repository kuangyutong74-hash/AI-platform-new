from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Database
    database_url: str = f"sqlite+aiosqlite:///{(PROJECT_DIR / 'story_cocreate.db').as_posix()}"

    # LLM (DeepSeek)
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("DEEPSEEK_API_KEY", "LLM_API_KEY"))
    llm_base_url: str = Field(default="https://api.deepseek.com/v1", validation_alias=AliasChoices("DEEPSEEK_BASE_URL", "LLM_BASE_URL"))
    llm_model: str = Field(default="deepseek-chat", validation_alias=AliasChoices("DEEPSEEK_MODEL", "LLM_MODEL"))

    # Free Microsoft Edge online TTS
    edge_tts_voice: str = "zh-CN-XiaoxiaoNeural"
    edge_tts_rate: str = "-8%"
    edge_tts_pitch: str = "+3Hz"

    # Story config
    max_turns: int = 15  # Soft safety cap; AI decides ending dynamically

    # App
    debug: bool = True

    # Story 模块的密钥配置与其运行目录同级，避免错误读取项目根目录的 .env。
    model_config = {"env_file": str(BACKEND_DIR / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
