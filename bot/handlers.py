from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.cooldown import Cooldown
from bot.protected import ProtectedUsers
from bot.quote_source import QuoteSource
from bot.responder import Responder
from bot.triggers import calls_bot_by_name, devops_topic, love_phrase, mentions_krasovska

router = Router(name="mrdevops")

GROUP_TYPES = ("group", "supergroup")
NO_ANSWER = "Шо? Я зараз не на звʼязку, пиши пізніше."
POLITE_NO_ANSWER = "Вибач, зараз не можу відповісти. Напиши трохи пізніше 🙂"


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
    responder: Responder | None,
    quotes: QuoteSource,
    cooldown: Cooldown,
    protected_users: ProtectedUsers,
) -> None:
    text = message.text or ""
    protected = protected_users.contains(message.from_user)

    # Красовська важливіша за все інше, відповідь завжди, без cooldown.
    # Про неї LLM нічого не генерує.
    if mentions_krasovska(text):
        await message.reply(love_phrase())
        return

    # Пряме звертання без cooldown: людина сама покликала бота
    if await is_addressed(message, bot):
        answer = await responder.answer(text, polite=protected) if responder else None
        if protected:
            # Захищеним ніколи не йде цитата з матами, навіть при збої LLM
            await message.reply(answer or POLITE_NO_ANSWER)
            return
        # Ліміт Gemini або збій: бот не мовчить, а кидає цитату з пулу
        await message.reply(answer or quotes.static_quote() or NO_ANSWER)
        return

    if protected:
        return

    # DevOps визначається ключовими словами, без LLM і без лімітів
    topic = devops_topic(text)
    if topic is None:
        return
    if not cooldown.ready(message.chat.id):
        return

    quote = await quotes.next_quote(topic)
    if quote is None:
        return

    await message.reply(quote)
    cooldown.mark(message.chat.id)
