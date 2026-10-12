from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфіг з змінних середовища та `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: SecretStr
    gemini_api_key: SecretStr | None = None

    # Модель для відповідей на звертання і генерації цитат.
    # Lite: без thinking, швидка, з більшим безкоштовним лімітом
    llm_model: str = "gemini-3.5-flash-lite"
    llm_enabled: bool = True

    # Режим цитат: static — пул по колу, generate — LLM, mixed — пул, далі LLM.
    # При збої LLM завжди береться цитата з пулу
    quote_mode: Literal["static", "generate", "mixed"] = "static"
    quotes_path: str = "quotes/quotes.yaml"

    # Пауза між DevOps-цитатами в одному чаті, секунди. 0 = без паузи
    cooldown_seconds: float = 0.0
    # З цими людьми бот не грубить: Telegram ID або @username через кому
    protected_users: str = ""
    # До цих людей бот звертається як до королеви. Вони автоматично захищені
    queen_users: str = ""
    # Шлях до heartbeat-файлу для Docker healthcheck
    heartbeat_path: str = "/tmp/mrdevops.heartbeat"
