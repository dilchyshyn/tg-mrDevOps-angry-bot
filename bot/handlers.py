from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.classifier import Classifier
from bot.cooldown import Cooldown
from bot.quote_source import QuoteSource

router = Router(name="mrdevops")

GROUP_TYPES = ("group", "supergroup")


def should_classify(text: str, min_length: int) -> bool:
    """Дешевий фільтр до LLM: достатньо довге повідомлення з літерами."""
    stripped = text.strip()
    return len(stripped) >= min_length and any(ch.isalpha() for ch in stripped)


@router.message(CommandStart(), F.chat.type == "private")
async def on_start(message: Message) -> None:
    await message.answer(
        "Я mrDevOps. Додай мене в групу, і коли хтось напише про девопс, "
        "я вкину пацанську цитату. Пиши в групу, тут я мовчу."
    )


@router.message(F.chat.type.in_(GROUP_TYPES), F.text)
async def on_group_text(
    message: Message,
    classifier: Classifier | None,
    quotes: QuoteSource,
    cooldown: Cooldown,
    min_text_length: int,
) -> None:
    text = message.text or ""
    if not should_classify(text, min_text_length):
        return
    if not cooldown.ready(message.chat.id):
        return
    if classifier is None:
        return

    verdict = await classifier.classify(text)
    if not verdict.devops:
        return

    quote = await quotes.next_quote(verdict.topic)
    if quote is None:
        return

    await message.reply(quote)
    cooldown.mark(message.chat.id)
