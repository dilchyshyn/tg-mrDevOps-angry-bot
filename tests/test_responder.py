from typing import Any

from bot.responder import ANSWER_PROMPT, MAX_ANSWER_LENGTH, POLITE_PROMPT, Responder


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, result: str | Exception) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return _FakeResponse(self._result)


class _FakeClient:
    """Імітує `genai.Client`: мокається ланцюжок `aio.models.generate_content`."""

    def __init__(self, result: str | Exception) -> None:
        self.aio = type("Aio", (), {"models": _FakeModels(result)})()


async def test_answer_returns_model_text() -> None:
    responder = Responder(_FakeClient("  відповідь  "), "model")  # type: ignore[arg-type]
    assert await responder.answer("питання") == "відповідь"


async def test_answer_api_error_is_none() -> None:
    responder = Responder(_FakeClient(RuntimeError("429")), "model")  # type: ignore[arg-type]
    assert await responder.answer("питання") is None


async def test_answer_empty_is_none() -> None:
    responder = Responder(_FakeClient("   "), "model")  # type: ignore[arg-type]
    assert await responder.answer("питання") is None


async def test_answer_is_truncated() -> None:
    responder = Responder(_FakeClient("а" * 5000), "model")  # type: ignore[arg-type]
    answer = await responder.answer("питання")
    assert answer is not None and len(answer) == MAX_ANSWER_LENGTH


async def test_polite_flag_switches_prompt() -> None:
    client = _FakeClient("ok")
    responder = Responder(client, "model")  # type: ignore[arg-type]
    await responder.answer("питання")
    await responder.answer("питання", polite=True)
    prompts = [call["config"].system_instruction for call in client.aio.models.calls]
    assert prompts == [ANSWER_PROMPT, POLITE_PROMPT]
