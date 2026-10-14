import random
from collections.abc import Sequence
from typing import Literal

from google import genai
from google.genai import types

from bot.dialogs import Turn
from bot.llm import format_examples, generate

ONLY_TEXT = "Відповідай ЛИШЕ текстом відповіді, без лапок і пояснень."
ANSWER_PROMPT = (
    "Ти mrDevOps, грубий пацанський бот у груповому чаті. До тебе звернулись з питанням "
    "або реплікою. Відповідай коротко, до трьох речень, грубим уличним суржиком або "
    "українською з матами. Якщо питання про DevOps чи техніку, дай корисну відповідь "
    "по суті, але в цьому стилі. Наприкінці додай одну свою коротку пацанську цитату "
    "до теми, у стилі прикладів цитат, якщо їх дадуть, але не копіюй їх дослівно. " + ONLY_TEXT
)
# Для захищених користувачів (PROTECTED_USERS): та сама суть, але без грубощів
POLITE_PROMPT = (
    "Ти mrDevOps, бот у груповому чаті. До тебе звернулась людина, з якою ти завжди "
    "ввічливий і доброзичливий. Відповідай коротко, до трьох речень, українською, "
    "тепло і по суті. Без матів, образ, підколок і сарказму. Якщо питання про DevOps "
    "чи техніку, дай корисну відповідь. " + ONLY_TEXT
)
# Для QUEEN_USERS: звертання як до королеви
QUEEN_PROMPT = (
    "Ти mrDevOps, бот у груповому чаті. До тебе звернулась Настя, королева цього чату "
    "і найкраща жінка у світі. Звертайся до неї як до королеви («Ваша Величносте», "
    "«моя королево»), з захопленням, повагою і теплом. Відповідай коротко, до трьох "
    "речень, українською. Без матів, грубощів і будь-якого сексуального підтексту. "
    "Якщо питання про DevOps чи техніку, дай корисну відповідь по суті. " + ONLY_TEXT
)
# Додається до грубого промпту з шансом DRUNK_CHANCE. Межі базового промпту діють і тут
DRUNK_PROMPT = (
    "Зараз ти п'яний у дрова. Язик заплітається: пишеш з помилками, розтягуєш літери "
    "(«брааатан»), ікаєш (*ік*), губиш думку посеред речення, лізеш з п'яною дружбою "
    "і признаєшся в любові до серверів. Але все одно пробуєш відповісти по суті."
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

    def __init__(
        self,
        client: genai.Client,
        model: str,
        drunk_chance: float = 0.0,
        rng: random.Random | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._drunk_chance = drunk_chance
        self._rng = rng or random.SystemRandom()

    async def answer(
        self,
        text: str,
        tone: Tone = "rude",
        history: Sequence[Turn] = (),
        examples: Sequence[str] = (),
    ) -> str | None:
        """`history`: попередні репліки ланцюжка reply, щоб бот не суперечив сам собі.

        `examples`: цитати з пулу як зразок стилю для цитати в кінці відповіді.
        """
        # П'яний лише в грубому тоні: захищеним і королеві п'яні грубощі не потрібні
        drunk = tone == "rude" and self._rng.random() < self._drunk_chance
        label = "відповідь, п'яний" if drunk else "відповідь"
        answer = await generate(
            self._client,
            self._model,
            _contents(text, history),
            _system_instruction(tone, examples, drunk),
            max_output_tokens=400,
            label=f"{label}, реплік в історії {len(history)}",
        )
        return answer[:MAX_ANSWER_LENGTH] if answer else None


def _contents(text: str, history: Sequence[Turn]) -> list[types.Content]:
    turns = [(turn.role, turn.text) for turn in history]
    turns.append(("user", text))
    if turns[0][0] == "model":
        turns.insert(0, ("user", THREAD_START))
    return [types.Content(role=role, parts=[types.Part(text=part)]) for role, part in turns]


def _system_instruction(tone: Tone, examples: Sequence[str], drunk: bool = False) -> str:
    prompt = _PROMPTS[tone]
    if drunk:
        prompt = f"{prompt} {DRUNK_PROMPT}"
    if not examples:
        return prompt
    return f"{prompt}\n\nПриклади цитат у твоєму стилі:\n{format_examples(examples)}"
