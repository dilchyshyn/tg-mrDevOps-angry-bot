import logging
import time
from collections.abc import Sequence
from typing import Literal

from google import genai
from google.genai import types

from bot.dialogs import Turn

logger = logging.getLogger(__name__)

ANSWER_PROMPT = (
    "Ти mrDevOps, грубий пацанський бот у груповому чаті. До тебе звернулись з питанням "
    "або реплікою. Відповідай коротко, до трьох речень, грубим уличним суржиком або "
    "українською з матами. Якщо питання про DevOps чи техніку, дай корисну відповідь "
    "по суті, але в цьому стилі. "
    "Заборонено: жарти про жінок і їхню сексуальність, національності, релігії, "
    "сексуальну орієнтацію, будь-яких конкретних людей, реальних осіб та брендів. "
    "Відповідай ЛИШЕ текстом відповіді, без лапок і пояснень."
)
# Для захищених користувачів (PROTECTED_USERS): та сама суть, але без грубощів
POLITE_PROMPT = (
    "Ти mrDevOps, бот у груповому чаті. До тебе звернулась людина, з якою ти завжди "
    "ввічливий і доброзичливий. Відповідай коротко, до трьох речень, українською, "
    "тепло і по суті. Без матів, образ, підколок і сарказму. Якщо питання про DevOps "
    "чи техніку, дай корисну відповідь. "
    "Відповідай ЛИШЕ текстом відповіді, без лапок і пояснень."
)
# Для QUEEN_USERS: звертання як до королеви
QUEEN_PROMPT = (
    "Ти mrDevOps, бот у груповому чаті. До тебе звернулась Настя, королева цього чату "
    "і найкраща жінка у світі. Звертайся до неї як до королеви («Ваша Величносте», "
    "«моя королево»), з захопленням, повагою і теплом. Відповідай коротко, до трьох "
    "речень, українською. Без матів, грубощів і будь-якого сексуального підтексту. "
    "Якщо питання про DevOps чи техніку, дай корисну відповідь по суті. "
    "Відповідай ЛИШЕ текстом відповіді, без лапок і пояснень."
)
MAX_ANSWER_LENGTH = 1000
# Gemini чекає, що розмова починається з репліки користувача
THREAD_START = "(початок розмови)"

Tone = Literal["rude", "polite", "queen"]
_PROMPTS: dict[Tone, str] = {
    "rude": ANSWER_PROMPT,
    "polite": POLITE_PROMPT,
    "queen": QUEEN_PROMPT,
}


class Responder:
    """Відповідь на пряме звертання до бота."""

    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    async def answer(
        self, text: str, tone: Tone = "rude", history: Sequence[Turn] = ()
    ) -> str | None:
        """`history`: попередні репліки ланцюжка reply, щоб бот не суперечив сам собі."""
        started = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=_contents(text, history),
                config=types.GenerateContentConfig(
                    system_instruction=_PROMPTS[tone],
                    max_output_tokens=400,
                ),
            )
        except Exception:
            logger.exception("Помилка відповіді на звертання")
            return None
        # Скільки чекали Gemini і на що пішли токени: роздуми теж сповільнюють відповідь
        usage = getattr(response, "usage_metadata", None)
        logger.info(
            "Gemini: %.1f с, реплік в історії %d, токени: вхід %s, вихід %s, роздуми %s",
            time.monotonic() - started,
            len(history),
            getattr(usage, "prompt_token_count", None),
            getattr(usage, "candidates_token_count", None),
            getattr(usage, "thoughts_token_count", None),
        )
        answer = (response.text or "").strip()
        if not answer:
            return None
        return answer[:MAX_ANSWER_LENGTH]


def _contents(text: str, history: Sequence[Turn]) -> list[types.Content]:
    turns = [(turn.role, turn.text) for turn in history]
    turns.append(("user", text))
    if turns[0][0] == "model":
        turns.insert(0, ("user", THREAD_START))
    return [types.Content(role=role, parts=[types.Part(text=part)]) for role, part in turns]
