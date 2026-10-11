import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from google import genai

from bot.classifier import Classifier
from bot.cooldown import Cooldown
from bot.handlers import router
from bot.quote_source import QuoteSource
from config.settings import Settings
from quotes.loader import load_quotes

logger = logging.getLogger("mrdevops")
HEARTBEAT_INTERVAL = 30


async def heartbeat(path: Path) -> None:
    """Оновлює файл, за яким Docker healthcheck розуміє, що процес живий."""
    while True:
        await asyncio.to_thread(path.write_text, "ok", encoding="utf-8")
        await asyncio.sleep(HEARTBEAT_INTERVAL)


async def run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    quotes = load_quotes(settings.quotes_path)
    logger.info("Завантажено цитат: %d", len(quotes))

    llm_client = None
    if settings.gemini_api_key is not None:
        llm_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    classifier = None
    if llm_client is not None and settings.llm_enabled:
        classifier = Classifier(llm_client, settings.llm_model)

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    dispatcher["classifier"] = classifier
    dispatcher["quotes"] = QuoteSource(
        quotes,
        mode=settings.quote_mode,
        client=llm_client,
        model=settings.llm_model,
    )
    dispatcher["cooldown"] = Cooldown(settings.cooldown_seconds)
    dispatcher["min_text_length"] = settings.min_text_length

    bot = Bot(token=settings.bot_token.get_secret_value())
    heartbeat_task = asyncio.create_task(heartbeat(Path(settings.heartbeat_path)))
    try:
        await dispatcher.start_polling(bot)
    finally:
        heartbeat_task.cancel()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    asyncio.run(run())


if __name__ == "__main__":
    main()
