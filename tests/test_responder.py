import random
from typing import Any

from bot.dialogs import Turn
from bot.responder import (
    ANSWER_PROMPT,
    DRUNK_PROMPT,
    MAX_ANSWER_LENGTH,
    POLITE_PROMPT,
    QUEEN_PROMPT,
    Responder,
    Tone,
)


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


async def test_tone_switches_prompt() -> None:
    client = _FakeClient("ok")
    responder = Responder(client, "model")  # type: ignore[arg-type]
    await responder.answer("питання")
    await responder.answer("питання", tone="polite")
    await responder.answer("питання", tone="queen")
    prompts = [call["config"].system_instruction for call in client.aio.models.calls]
    assert prompts == [ANSWER_PROMPT, POLITE_PROMPT, QUEEN_PROMPT]


async def test_history_is_sent_as_turns() -> None:
    client = _FakeClient("ok")
    responder = Responder(client, "model")  # type: ignore[arg-type]
    history = [Turn("user", "питання", None), Turn("model", "відповідь", 1)]
    await responder.answer("а чому?", history=history)
    contents = client.aio.models.calls[0]["contents"]
    assert [(c.role, c.parts[0].text) for c in contents] == [
        ("user", "питання"),
        ("model", "відповідь"),
        ("user", "а чому?"),
    ]


async def test_history_starting_with_bot_gets_user_turn_first() -> None:
    client = _FakeClient("ok")
    responder = Responder(client, "model")  # type: ignore[arg-type]
    await responder.answer("чого?", history=[Turn("model", "цитата", None)])
    roles = [c.role for c in client.aio.models.calls[0]["contents"]]
    assert roles == ["user", "model", "user"]


async def test_examples_are_added_to_system_instruction() -> None:
    client = _FakeClient("ok")
    responder = Responder(client, "model")  # type: ignore[arg-type]
    await responder.answer("питання", examples=["цитата раз", "цитата два"])
    prompt = client.aio.models.calls[0]["config"].system_instruction
    assert prompt.startswith(ANSWER_PROMPT)
    assert "- цитата раз" in prompt and "- цитата два" in prompt


class _FixedRandom(random.Random):
    def __init__(self, value: float) -> None:
        super().__init__()
        self._value = value

    def random(self) -> float:
        return self._value


async def _prompt(drunk_chance: float, roll: float, tone: Tone = "rude") -> str:
    client = _FakeClient("ok")
    responder = Responder(client, "model", drunk_chance, rng=_FixedRandom(roll))  # type: ignore[arg-type]
    await responder.answer("питання", tone=tone)
    prompt: str = client.aio.models.calls[0]["config"].system_instruction
    return prompt


async def test_drunk_when_roll_below_chance() -> None:
    prompt = await _prompt(0.1, 0.05)
    assert prompt.startswith(ANSWER_PROMPT) and DRUNK_PROMPT in prompt


async def test_sober_when_roll_above_chance() -> None:
    assert DRUNK_PROMPT not in await _prompt(0.1, 0.5)


async def test_never_drunk_with_zero_chance() -> None:
    assert DRUNK_PROMPT not in await _prompt(0.0, 0.0)


async def test_protected_and_queen_are_never_drunk() -> None:
    assert DRUNK_PROMPT not in await _prompt(1.0, 0.0, tone="polite")
    assert DRUNK_PROMPT not in await _prompt(1.0, 0.0, tone="queen")
