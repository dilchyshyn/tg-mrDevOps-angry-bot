from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from bot.classifier import Verdict
from bot.cooldown import Cooldown
from bot.handlers import NO_ANSWER, on_group_text
from bot.triggers import LOVE_PHRASES

BOT_ID = 42


def _message(text: str, reply_from_id: int | None = None) -> Any:
    reply = None
    if reply_from_id is not None:
        reply = SimpleNamespace(from_user=SimpleNamespace(id=reply_from_id))
    return SimpleNamespace(
        text=text, chat=SimpleNamespace(id=1), reply_to_message=reply, reply=AsyncMock()
    )


def _bot() -> Any:
    return SimpleNamespace(
        id=BOT_ID, me=AsyncMock(return_value=SimpleNamespace(username="TestBot"))
    )


async def _handle(message: Any, **overrides: Any) -> dict[str, Any]:
    deps: dict[str, Any] = {
        "bot": _bot(),
        "classifier": SimpleNamespace(classify=AsyncMock(return_value=Verdict(True, "k8s"))),
        "responder": SimpleNamespace(answer=AsyncMock(return_value="відповідь")),
        "quotes": SimpleNamespace(next_quote=AsyncMock(return_value="цитата")),
        "cooldown": Cooldown(60, clock=lambda: 0.0),
        "min_text_length": 8,
    }
    deps.update(overrides)
    await on_group_text(message, **deps)
    return deps


async def test_krasovska_gets_love_without_llm() -> None:
    message = _message("мрдевопс, що думаєш про Красовську?")
    deps = await _handle(message)
    assert message.reply.await_args.args[0] in LOVE_PHRASES
    deps["responder"].answer.assert_not_awaited()
    deps["classifier"].classify.assert_not_awaited()


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
    deps["classifier"].classify.assert_not_awaited()


async def test_reply_to_bot_is_answered() -> None:
    message = _message("а чому так?", reply_from_id=BOT_ID)
    await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")


async def test_username_mention_is_answered() -> None:
    message = _message("@testbot ти живий?")
    await _handle(message)
    message.reply.assert_awaited_once_with("відповідь")


async def test_name_call_without_llm_gets_fallback() -> None:
    message = _message("мрдевопс привіт")
    await _handle(message, responder=None)
    message.reply.assert_awaited_once_with(NO_ANSWER)


async def test_devops_message_gets_quote() -> None:
    message = _message("у нас знову впав под")
    await _handle(message)
    message.reply.assert_awaited_once_with("цитата")


async def test_non_devops_message_is_ignored() -> None:
    message = _message("хто йде на піцу?")
    classifier = SimpleNamespace(classify=AsyncMock(return_value=Verdict(False)))
    await _handle(message, classifier=classifier)
    message.reply.assert_not_awaited()
