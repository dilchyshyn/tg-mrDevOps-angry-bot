from bot.llm import format_examples, generate
from tests.fakes import FakeGeminiClient


async def test_generate_returns_stripped_text() -> None:
    client = FakeGeminiClient("  текст  ")
    result = await generate(client, "m", "запит", "система", 50, label="тест")  # type: ignore[arg-type]
    assert result == "текст"
    config = client.calls[0]["config"]
    assert config.system_instruction == "система" and config.max_output_tokens == 50


async def test_generate_error_is_none() -> None:
    client = FakeGeminiClient(RuntimeError("429"))
    assert await generate(client, "m", "запит", "система", 50, label="тест") is None  # type: ignore[arg-type]


async def test_generate_empty_is_none() -> None:
    client = FakeGeminiClient("   ")
    assert await generate(client, "m", "запит", "система", 50, label="тест") is None  # type: ignore[arg-type]


def test_format_examples() -> None:
    assert format_examples(["раз", "два"]) == "- раз\n- два"
