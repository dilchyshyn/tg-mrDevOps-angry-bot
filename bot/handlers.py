from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from bot.cooldown import Cooldown
from bot.dialogs import Dialogs, Turn
from bot.protected import ProtectedUsers
from bot.quote_source import QuoteSource
from bot.responder import Responder, Tone
from bot.triggers import (
    calls_bot_by_name,
    devops_topic,
    love_phrase,
    mentions_krasovska,
    queen_phrase,
)

router = Router(name="mrdevops")

GROUP_TYPES = ("group", "supergroup")
NO_ANSWER = "Шо? Я зараз не на звʼязку, пиши пізніше."
POLITE_NO_ANSWER = "Вибач, зараз не можу відповісти. Напиши трохи пізніше 🙂"


def reply_to_bot(message: Message, bot: Bot) -> Message | None:
    """Повідомлення бота, на яке відповіли, або `None`."""
    reply = message.reply_to_message
    if reply is not None and reply.from_user is not None and reply.from_user.id == bot.id:
        return reply
    return None


async def is_addressed(message: Message, bot: Bot) -> bool:
    """Звертання до бота: на ім'я, через @username або reply на його повідомлення."""
    text = message.text or ""
    if calls_bot_by_name(text):
        return True
    if reply_to_bot(message, bot) is not None:
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
    queen_users: ProtectedUsers,
    dialogs: Dialogs,
) -> None:
    text = message.text or ""
    queen = queen_users.contains(message.from_user)
    protected = queen or protected_users.contains(message.from_user)
    tone: Tone = "queen" if queen else "polite" if protected else "rude"

    # Красовська важливіша за все інше, відповідь завжди, без cooldown.
    # Про неї LLM нічого не генерує.
    if mentions_krasovska(text):
        await message.reply(love_phrase())
        return

    # Пряме звертання без cooldown: людина сама покликала бота
    if await is_addressed(message, bot):
        # Reply на бота: Gemini бачить попередні репліки ланцюжка, щоб не суперечити собі
        parent = reply_to_bot(message, bot)
        history: list[Turn] = []
        if parent is not None:
            history = dialogs.thread(message.chat.id, parent.message_id)
            if not history and parent.text:
                # Ланцюжка немає (рестарт, DevOps-цитата): хоча б те, на що відповіли
                history = [Turn("model", parent.text, None)]

        answer = None
        if responder is not None:
            # «друкує…» у чаті, поки чекаємо Gemini: кілька секунд не виглядають як мовчання
            async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
                answer = await responder.answer(text, tone=tone, history=history)
        if queen:
            reply_text = answer or queen_phrase()
        elif protected:
            # Захищеним ніколи не йде цитата з матами, навіть при збої LLM
            reply_text = answer or POLITE_NO_ANSWER
        else:
            # Ліміт Gemini або збій: бот не мовчить, а кидає цитату з пулу
            reply_text = answer or quotes.static_quote() or NO_ANSWER

        sent = await message.reply(reply_text)
        parent_id = parent.message_id if parent is not None else None
        dialogs.add(message.chat.id, message.message_id, "user", text, parent_id)
        dialogs.add(message.chat.id, sent.message_id, "model", reply_text, message.message_id)
        return

    # Королеві на DevOps замість грубої цитати комплімент, звичайні повідомлення без реакції
    if queen:
        if devops_topic(text) is not None:
            await message.reply(queen_phrase())
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
