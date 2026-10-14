import logging
import time
from collections.abc import Sequence

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


async def generate(
    client: genai.Client,
    model: str,
    contents: str | list[types.Content],
    system_instruction: str,
    max_output_tokens: int,
    label: str,
) -> str | None:
    """Один виклик Gemini. Збій або порожня відповідь дають `None`, винятків немає.

    `label` іде в лог разом з часом і токенами, щоб бачити, звідки затримка.
    """
    started = time.monotonic()
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens,
            ),
        )
    except Exception:
        logger.exception("Помилка Gemini (%s)", label)
        return None
    # Роздуми теж сповільнюють відповідь, тому їх видно окремо
    usage = getattr(response, "usage_metadata", None)
    logger.info(
        "Gemini (%s): %.1f с, токени: вхід %s, вихід %s, роздуми %s",
        label,
        time.monotonic() - started,
        getattr(usage, "prompt_token_count", None),
        getattr(usage, "candidates_token_count", None),
        getattr(usage, "thoughts_token_count", None),
    )
    return (response.text or "").strip() or None


def format_examples(examples: Sequence[str]) -> str:
    """Цитати з пулу списком для промпту."""
    return "\n".join(f"- {example}" for example in examples)
