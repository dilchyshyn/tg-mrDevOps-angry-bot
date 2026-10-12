import logging
import random
from collections.abc import Sequence
from typing import Literal

from google import genai
from google.genai import types

from quotes.loader import Quote

logger = logging.getLogger(__name__)

QuoteMode = Literal["static", "generate", "mixed"]

GENERATE_PROMPT = (
    "Ти пишеш одну коротку пацанську цитату для чату. Тема може бути DevOps або життя. "
    "Стиль: грубий уличний суржик або українська з матами, як у реальних пацанів. "
    "Заборонено: жарти про жінок і їхню сексуальність, національності, релігії, "
    "сексуальну орієнтацію, будь-яких конкретних людей, реальних осіб та брендів. "
    "Відповідай ЛИШЕ текстом цитати, одним рядком, до 200 символів, без лапок і пояснень."
)
MAX_GENERATED_LENGTH = 200


def pick_static(quotes: Sequence[Quote], used: set[str], rng: random.Random) -> Quote | None:
    """Випадкова цитата, якої ще не було. None, якщо пул вичерпано."""
    available = [q for q in quotes if q.id not in used]
    if not available:
        return None
    quote = rng.choice(available)
    used.add(quote.id)
    return quote


class QuoteSource:
    """Вибір цитати. static: пул по колу; generate: LLM; mixed: пул, після вичерпання LLM.

    Якщо LLM недоступна або впала, завжди повертається цитата з пулу.
    """

    def __init__(
        self,
        quotes: Sequence[Quote],
        mode: QuoteMode,
        client: genai.Client | None,
        model: str,
        rng: random.Random | None = None,
    ) -> None:
        self._quotes = list(quotes)
        self._mode = mode
        self._client = client
        self._model = model
        self._used: set[str] = set()
        self._rng = rng or random.Random()

    def static_quote(self) -> str | None:
        """Цитата з пулу без повторів у межах кола. None лише для порожнього пулу."""
        quote = pick_static(self._quotes, self._used, self._rng)
        if quote is None:
            self._used.clear()
            quote = pick_static(self._quotes, self._used, self._rng)
        return quote.text if quote is not None else None

    async def next_quote(self, topic: str) -> str | None:
        pool_exhausted = len(self._used) >= len(self._quotes)
        if self._mode == "generate" or (self._mode == "mixed" and pool_exhausted):
            generated = await self._generate(topic)
            if generated is not None:
                return generated
        return self.static_quote()

    async def _generate(self, topic: str) -> str | None:
        if self._client is None:
            logger.warning("Генерація цитат вимкнена: немає GEMINI_API_KEY")
            return None
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=f"Тема: {topic or 'девопс'}",
                config=types.GenerateContentConfig(
                    system_instruction=GENERATE_PROMPT,
                    max_output_tokens=120,
                ),
            )
        except Exception:
            logger.exception("Помилка генерації цитати")
            return None
        text = (response.text or "").strip().strip('"«»').strip()
        if not text or len(text) > MAX_GENERATED_LENGTH:
            return None
        return text
