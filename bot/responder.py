import logging
from typing import Literal

from google import genai
from google.genai import types

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

    async def answer(self, text: str, tone: Tone = "rude") -> str | None:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=_PROMPTS[tone],
                    max_output_tokens=400,
                ),
            )
        except Exception:
            logger.exception("Помилка відповіді на звертання")
            return None
        answer = (response.text or "").strip()
        if not answer:
            return None
        return answer[:MAX_ANSWER_LENGTH]
