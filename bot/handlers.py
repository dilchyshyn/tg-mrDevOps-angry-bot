from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.classifier import Classifier
from bot.cooldown import Cooldown
from bot.quote_source import QuoteSource
from bot.responder import Responder
from bot.triggers import calls_bot_by_name, love_phrase, mentions_krasovska

router = Router(name="mrdevops")

GROUP_TYPES = ("group", "supergroup")
NO_ANSWER = "Шо? Я зараз не на звʼязку, пиши пізніше."


def should_classify(text: str, min_length: int) -> bool:
    """Дешевий фільтр до LLM: достатньо довге повідомлення з літерами."""
    stripped = text.strip()
    return len(stripped) >= min_length and any(ch.isalpha() for ch in stripped)


async def is_addressed(message: Message, bot: Bot) -> bool:
    """Звертання до бота: на ім'я, через @username або reply на його повідомлення."""
    text = message.text or ""
    if calls_bot_by_name(text):
        return True
    reply = message.reply_to_message
    if reply is not None and reply.from_user is not None and reply.from_user.id == bot.id:
        return True
    me = await bot.me()
    return me.username is not None and f"@{me.username.lower()}" in text.lower()


@router.message(CommandStart(), F.chat.type == "private")
async def on_start(message: Message) -> None:
    await message.answer(
        "Я mrDevOps. Додай мене в групу, і коли хтось напише про девопс, "
        "я вкину пацанську цитату. Пиши в групу, тут я мовчу."
    )


@router.message(F.chat.type.in_(GROUP_TYPES), F.text)
async def on_group_text(
    message: Message,
    bot: Bot,
    classifier: Classifier | None,
    responder: Responder | None,
    quotes: QuoteSource,
    cooldown: Cooldown,
    min_text_length: int,
) -> None:
    text = message.text or ""

    # Красовська важливіша за все інше, відповідь завжди, без cooldown.
    # Про неї LLM нічого не генерує.
    if mentions_krasovska(text):
        await message.reply(love_phrase())
        return

    # Пряме звертання без cooldown: людина сама покликала бота
    if await is_addressed(message, bot):
        answer = await responder.answer(text) if responder is not None else None
        await message.reply(answer or NO_ANSWER)
        return

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
