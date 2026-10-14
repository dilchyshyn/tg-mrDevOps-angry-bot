from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

from bot.cooldown import Cooldown
from bot.dialogs import Dialogs, Turn
from bot.handlers import NO_ANSWER, POLITE_NO_ANSWER, on_group_text
from bot.protected import ProtectedUsers
from bot.triggers import LOVE_PHRASES, QUEEN_PHRASES

BOT_ID = 42


def _message(
    text: str,
    reply_from_id: int | None = None,
    user_id: int = 7,
    username: str | None = "vasya",
    message_id: int = 100,
    reply_id: int = 50,
    reply_text: str | None = "попередня відповідь",
) -> Any:
    reply = None
    if reply_from_id is not None:
        reply = SimpleNamespace(
            message_id=reply_id, text=reply_text, from_user=SimpleNamespace(id=reply_from_id)
        )
    return SimpleNamespace(
        message_id=message_id,
        text=text,
        chat=SimpleNamespace(id=1),
        from_user=SimpleNamespace(id=user_id, username=username),
        reply_to_message=reply,
        reply=AsyncMock(return_value=SimpleNamespace(message_id=message_id + 1)),
    )


def _bot() -> Any:
    return SimpleNamespace(
        id=BOT_ID, me=AsyncMock(return_value=SimpleNamespace(username="TestBot"))
    )


def _quotes(static: str | None = "пул") -> Any:
    return SimpleNamespace(
        next_quote=AsyncMock(return_value="цитата"), static_quote=Mock(return_value=static)
    )


async def _handle(message: Any, **overrides: Any) -> dict[str, Any]:
    deps: dict[str, Any] = {
        "bot": _bot(),
        "responder": SimpleNamespace(answer=AsyncMock(return_value="відповідь")),
        "quotes": _quotes(),
        "cooldown": Cooldown(0),
        "protected_users": ProtectedUsers.parse("@Kate, 555"),
        "queen_users": ProtectedUsers.parse("@nastya"),
        "dialogs": Dialogs(),
    }
    deps.update(overrides)
    await on_group_text(message, **deps)
    return deps


async def test_krasovska_gets_love_without_llm() -> None:
    message = _message("мрдевопс, що думаєш про Красовську на проді?")
    deps = await _handle(message)
    assert message.reply.await_args.args[0] in LOVE_PHRASES
    deps["responder"].answer.assert_not_awaited()
    deps["quotes"].next_quote.assert_not_awaited()


async def test_krasovska_is_answered_every_time() -> None:
    cooldown = Cooldown(60, clock=lambda: 0.0)
    cooldown.mark(1)
    for _ in range(3):
        message = _message("красовська")
        await _handle(message, cooldown=cooldown)
        message.reply.assert_awaited_once()


async def test_name_call_is_answered_even_in_cooldown() -> None:
    cooldown = Cooldown(60, clock=lambda: 0.0)
    cooldown.mark(1)
    message = _message("мрдевопс, що таке helm?")
    deps = await _handle(message, cooldown=cooldown)
    message.reply.assert_awaited_once_with("відповідь")
    deps["quotes"].next_quote.assert_not_awaited()


async def test_reply_to_bot_is_answered() -> None:
    message = _message("а чому так?", reply_from_id=BOT_ID)
    await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")


async def test_username_mention_is_answered() -> None:
    message = _message("@testbot ти живий?")
    await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")


async def test_name_call_on_llm_failure_gets_pool_quote() -> None:
    message = _message("мрдевопс привіт")
    responder = SimpleNamespace(answer=AsyncMock(return_value=None))
    await _handle(message, responder=responder)
    message.reply.assert_awaited_once_with("пул")


async def test_name_call_without_llm_and_pool_gets_fallback() -> None:
    message = _message("мрдевопс привіт")
    await _handle(message, responder=None, quotes=_quotes(static=None))
    message.reply.assert_awaited_once_with(NO_ANSWER)


async def test_devops_keyword_gets_quote_with_topic() -> None:
    message = _message("у нас знову впав под")
    deps = await _handle(message)
    message.reply.assert_awaited_once_with("цитата")
    deps["quotes"].next_quote.assert_awaited_once_with("kubernetes")


async def test_devops_respects_cooldown_when_set() -> None:
    cooldown = Cooldown(60, clock=lambda: 0.0)
    cooldown.mark(1)
    message = _message("деплой впав")
    await _handle(message, cooldown=cooldown)
    message.reply.assert_not_awaited()


async def test_regular_chat_is_ignored() -> None:
    message = _message("хто йде на піцу?")
    deps = await _handle(message)
    message.reply.assert_not_awaited()
    deps["quotes"].next_quote.assert_not_awaited()


async def test_protected_user_gets_no_devops_quote() -> None:
    message = _message("деплой знову впав", username="kate")
    deps = await _handle(message)
    message.reply.assert_not_awaited()
    deps["quotes"].next_quote.assert_not_awaited()


async def test_protected_user_by_id_gets_polite_answer() -> None:
    message = _message("мрдевопс, що таке docker?", user_id=555, username=None)
    deps = await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")
    deps["responder"].answer.assert_awaited_once_with(
        "мрдевопс, що таке docker?", tone="polite", history=[]
    )


async def test_protected_user_never_gets_pool_quote_on_llm_failure() -> None:
    message = _message("мрдевопс привіт", username="KATE")
    responder = SimpleNamespace(answer=AsyncMock(return_value=None))
    deps = await _handle(message, responder=responder)
    message.reply.assert_awaited_once_with(POLITE_NO_ANSWER)
    deps["quotes"].static_quote.assert_not_called()


async def test_regular_user_gets_rude_answer() -> None:
    message = _message("мрдевопс привіт")
    deps = await _handle(message)
    deps["responder"].answer.assert_awaited_once_with("мрдевопс привіт", tone="rude", history=[])


async def test_protected_user_still_gets_krasovska_phrase() -> None:
    message = _message("Красовська", username="kate")
    await _handle(message)
    assert message.reply.await_args.args[0] in LOVE_PHRASES


async def test_queen_gets_royal_answer() -> None:
    message = _message("мрдевопс, що таке kubernetes?", username="Nastya")
    deps = await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")
    deps["responder"].answer.assert_awaited_once_with(
        "мрдевопс, що таке kubernetes?", tone="queen", history=[]
    )


async def test_queen_gets_phrase_when_llm_fails() -> None:
    message = _message("мрдевопс привіт", username="nastya")
    responder = SimpleNamespace(answer=AsyncMock(return_value=None))
    deps = await _handle(message, responder=responder)
    assert message.reply.await_args.args[0] in QUEEN_PHRASES
    deps["quotes"].static_quote.assert_not_called()


async def test_queen_devops_message_gets_compliment_not_quote() -> None:
    message = _message("деплой знову впав", username="nastya")
    deps = await _handle(message)
    assert message.reply.await_args.args[0] in QUEEN_PHRASES
    deps["quotes"].next_quote.assert_not_awaited()


async def test_queen_regular_message_is_ignored() -> None:
    message = _message("хто йде на піцу?", username="nastya")
    await _handle(message)
    message.reply.assert_not_awaited()


async def test_reply_to_bot_passes_thread_history() -> None:
    dialogs = Dialogs()
    first = _message("мрдевопс, що краще, docker чи podman?", message_id=10)
    await _handle(first, dialogs=dialogs)

    second = _message("а ти ж казав інше?", reply_from_id=BOT_ID, message_id=20, reply_id=11)
    deps = await _handle(second, dialogs=dialogs)
    history = deps["responder"].answer.await_args.kwargs["history"]
    assert [(turn.role, turn.text) for turn in history] == [
        ("user", "мрдевопс, що краще, docker чи podman?"),
        ("model", "відповідь"),
    ]

    third = _message("ну і?", reply_from_id=BOT_ID, message_id=30, reply_id=21)
    deps = await _handle(third, dialogs=dialogs)
    history = deps["responder"].answer.await_args.kwargs["history"]
    assert [turn.text for turn in history] == [
        "мрдевопс, що краще, docker чи podman?",
        "відповідь",
        "а ти ж казав інше?",
        "відповідь",
    ]


async def test_reply_to_unknown_bot_message_uses_its_text() -> None:
    message = _message("чого ти так?", reply_from_id=BOT_ID, reply_text="стара цитата")
    deps = await _handle(message)
    history = deps["responder"].answer.await_args.kwargs["history"]
    assert history == [Turn("model", "стара цитата", None)]


async def test_reply_to_other_user_has_no_history() -> None:
    message = _message("мрдевопс, глянь", reply_from_id=999)
    deps = await _handle(message)
    assert deps["responder"].answer.await_args.kwargs["history"] == []


async def test_fallback_answer_is_remembered_in_thread() -> None:
    dialogs = Dialogs()
    responder = SimpleNamespace(answer=AsyncMock(return_value=None))
    await _handle(_message("мрдевопс привіт", message_id=10), responder=responder, dialogs=dialogs)
    assert [turn.text for turn in dialogs.thread(1, 11)] == ["мрдевопс привіт", "пул"]
