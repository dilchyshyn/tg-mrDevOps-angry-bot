from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфіг з змінних середовища та `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: SecretStr
    gemini_api_key: SecretStr | None = None

    # Модель для класифікації та генерації цитат (Flash — швидко і з безкоштовним рівнем)
    llm_model: str = "gemini-2.5-flash"
    llm_enabled: bool = True

    # Режим цитат: static — лише пул, generate — лише LLM, mixed — пул, далі LLM
    quote_mode: Literal["static", "generate", "mixed"] = "mixed"
    quotes_path: str = "quotes/quotes.yaml"

    # Повідомлення коротше за це не класифікуються (економія токенів)
    min_text_length: int = 8
    # Пауза між відповідями в одному чаті, секунди
    cooldown_seconds: float = 60.0
    # Шлях до heartbeat-файлу для Docker healthcheck
    heartbeat_path: str = "/tmp/mrdevops.heartbeat"
