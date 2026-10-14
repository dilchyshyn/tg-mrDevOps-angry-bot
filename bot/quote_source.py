import json
import logging
import os
import random
from collections import deque
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Literal

from google import genai
from google.genai import types

from quotes.loader import Quote

logger = logging.getLogger(__name__)

QuoteMode = Literal["static", "generate", "mixed"]

GENERATE_PROMPT = (
    "Ти пишеш одну коротку пацанську цитату у відповідь на повідомлення в чаті. "
    "Цитата має бути влучною саме до цього повідомлення і його теми, а не загальною. "
    "Стиль бери з прикладів цитат, які дадуть разом з повідомленням, але не копіюй їх. "
    "Стиль: грубий уличний суржик або українська з матами, як у реальних пацанів. "
    "Заборонено: жарти про жінок і їхню сексуальність, національності, релігії, "
    "сексуальну орієнтацію, будь-яких конкретних людей, реальних осіб та брендів. "
    "Відповідай ЛИШЕ текстом цитати, одним рядком, до 200 символів, без лапок і пояснень."
)
MAX_GENERATED_LENGTH = 200
MAX_MESSAGE_LENGTH = 500
# Скільки цитат з пулу дати Gemini як зразок стилю
EXAMPLES_COUNT = 5

# Тема з `devops_topic` → теги цитат у quotes.yaml, щоб цитата з пулу була влучною
TOPIC_TAGS: dict[str, frozenset[str]] = {
    "docker": frozenset({"docker"}),
    "kubernetes": frozenset({"k8s", "helm"}),
    "деплой": frozenset({"deploy", "rollback"}),
    "ci/cd": frozenset({"cicd"}),
    "інфраструктура": frozenset({"terraform", "ansible", "nginx", "linux"}),
    "моніторинг": frozenset({"monitoring", "logs"}),
    "прод": frozenset({"prod", "backup"}),
    "девопс": frozenset({"general", "git", "backup"}),
}
# Частка пулу, яка не повторюється навіть на стику кіл
RECENT_SHARE = 3


def pick_static(
    quotes: Sequence[Quote],
    used: set[str],
    rng: random.Random,
    recent: Collection[str] = (),
    tags: Collection[str] = (),
) -> Quote | None:
    """Випадкова цитата, якої ще не було в колі. None, якщо пул вичерпано.

    Нещодавно показані (`recent`) пропускаються, поки є з чого вибрати.
    Серед решти перевага цитатам з тегами теми (`tags`), якщо такі є.
    """
    available = [q for q in quotes if q.id not in used]
    if not available:
        return None
    fresh = [q for q in available if q.id not in recent] or available
    on_topic = [q for q in fresh if not set(q.tags).isdisjoint(tags)]
    quote = rng.choice(on_topic or fresh)
    used.add(quote.id)
    return quote


class QuoteSource:
    """Вибір цитати. static: пул по колу; generate: LLM; mixed: пул, після вичерпання LLM.

    Цитата з пулу підбирається за темою повідомлення. LLM пише нову цитату під саме
    повідомлення, взявши кілька цитат з пулу за зразок стилю.
    Якщо LLM недоступна або впала, завжди повертається цитата з пулу.
    """

    def __init__(
        self,
        quotes: Sequence[Quote],
        mode: QuoteMode,
        client: genai.Client | None,
        model: str,
        rng: random.Random | None = None,
        state_path: Path | None = None,
    ) -> None:
        self._quotes = list(quotes)
        self._mode = mode
        self._client = client
        self._model = model
        self._used: set[str] = set()
        # Останні показані: на початку нового кола вони не йдуть одразу знову
        self._recent: deque[str] = deque(maxlen=len(self._quotes) // RECENT_SHARE)
        self._rng = rng or random.SystemRandom()
        # Файл стану на docker volume, щоб коло не скидалось після рестарту і деплою
        self._state_path = state_path
        self._load_state()

    def static_quote(self, topic: str | None = None) -> str | None:
        """Цитата з пулу без повторів у межах кола і без повтору недавніх на стику кіл.

        З темою (`topic`) перевага цитатам з її тегами. None лише для порожнього пулу.
        """
        tags = TOPIC_TAGS.get(topic or "", frozenset())
        quote = pick_static(self._quotes, self._used, self._rng, self._recent, tags)
        if quote is None:
            self._used.clear()
            quote = pick_static(self._quotes, self._used, self._rng, self._recent, tags)
        if quote is None:
            return None
        self._recent.append(quote.id)
        self._save_state()
        return quote.text

    def examples(self, topic: str | None = None, count: int = EXAMPLES_COUNT) -> list[str]:
        """Кілька цитат з пулу як зразок стилю для LLM, спершу за темою. Коло не чіпає."""
        tags = TOPIC_TAGS.get(topic or "", frozenset())
        on_topic = [q for q in self._quotes if not set(q.tags).isdisjoint(tags)]
        others = [q for q in self._quotes if set(q.tags).isdisjoint(tags)]
        picked = self._rng.sample(on_topic, min(count // 2 + 1, len(on_topic)))
        picked += self._rng.sample(others, min(count - len(picked), len(others)))
        return [q.text for q in picked]

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))
            used, recent = state["used"], state["recent"]
        except Exception:
            logger.exception("Не вдалось прочитати стан цитат, починаю з нуля")
            return
        # Пул міг змінитись між деплоями: id, яких уже немає, відкидаються
        known = {q.id for q in self._quotes}
        self._used = {i for i in used if i in known}
        self._recent.extend(i for i in recent if i in known)
        logger.info("Стан цитат відновлено: показано %d з %d", len(self._used), len(known))

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        state = {"used": sorted(self._used), "recent": list(self._recent)}
        tmp = self._state_path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(state), encoding="utf-8")
            os.replace(tmp, self._state_path)
        except OSError:
            logger.exception("Не вдалось зберегти стан цитат")

    async def next_quote(self, topic: str, text: str = "") -> str | None:
        """Цитата у відповідь на повідомлення `text` з темою `topic`."""
        pool_exhausted = len(self._used) >= len(self._quotes)
        if self._mode == "generate" or (self._mode == "mixed" and pool_exhausted):
            generated = await self._generate(topic, text)
            if generated is not None:
                return generated
        return self.static_quote(topic)

    async def _generate(self, topic: str, text: str) -> str | None:
        if self._client is None:
            logger.warning("Генерація цитат вимкнена: немає GEMINI_API_KEY")
            return None
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=_generate_request(topic, text, self.examples(topic)),
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


def _generate_request(topic: str, text: str, examples: Sequence[str]) -> str:
    lines = [f"Тема: {topic or 'девопс'}"]
    if text:
        lines.append(f"Повідомлення: {text[:MAX_MESSAGE_LENGTH]}")
    lines.append("Приклади цитат у потрібному стилі:")
    lines += [f"- {example}" for example in examples]
    return "\n".join(lines)
