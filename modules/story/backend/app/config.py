from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
PLATFORM_DIR = BACKEND_DIR.parents[2]


class Settings(BaseSettings):
    # Database
    database_url: str = f"sqlite+aiosqlite:///{(PROJECT_DIR / 'story_cocreate.db').as_posix()}"

    # OpenAI-compatible LLM. Generic/Zhipu names take priority; legacy DeepSeek names remain supported.
    llm_api_key: str = Field(default="", validation_alias=AliasChoices("AI_API_KEY", "ZHIPUAI_API_KEY", "ZHIPU_API_KEY", "LLM_API_KEY", "DEEPSEEK_API_KEY"))
    llm_base_url: str = Field(default="https://api.deepseek.com/v1", validation_alias=AliasChoices("AI_BASE_URL", "AI_API_BASE", "ZHIPUAI_BASE_URL", "ZHIPU_BASE_URL", "LLM_BASE_URL", "DEEPSEEK_BASE_URL"))
    llm_model: str = Field(default="deepseek-chat", validation_alias=AliasChoices("AI_MODEL", "ZHIPUAI_MODEL", "ZHIPU_MODEL", "LLM_MODEL", "DEEPSEEK_MODEL"))

    # Free Microsoft Edge online TTS
    edge_tts_voice: str = "zh-CN-XiaoxiaoNeural"
    edge_tts_rate: str = "-6%"
    edge_tts_pitch: str = "+2Hz"
    edge_tts_proxy: str = Field(default="", validation_alias=AliasChoices("TTS_PROXY", "HTTPS_PROXY", "HTTP_PROXY"))

    # Story config
    max_turns: int = 15  # Soft safety cap; AI decides ending dynamically

    # App
    debug: bool = True

    # 四个探索模块统一读取整合平台根目录的 DeepSeek 配置。
    model_config = {"env_file": str(PLATFORM_DIR / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
