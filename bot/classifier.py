import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = (
    "Ти класифікатор повідомлень із групового чату. Визнач, чи повідомлення стосується "
    "DevOps (контейнери, Kubernetes, CI/CD, деплой, інфраструктура, сервери, мережа, "
    "моніторинг, логи, бекапи, Terraform, Ansible, git-процеси тощо). "
    "Відповідай ЛИШЕ JSON без пояснень: "
    '{"devops": true|false, "topic": "коротка тема або порожньо"}.'
)


@dataclass(frozen=True)
class Verdict:
    devops: bool
    topic: str = ""


NEGATIVE = Verdict(devops=False)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_verdict(raw: str) -> Verdict:
    """Витягує вердикт з відповіді моделі. Будь-який збій трактується як "не DevOps"."""
    match = _JSON_RE.search(raw)
    if match is None:
        return NEGATIVE
    try:
        data: Any = json.loads(match.group(0))
    except json.JSONDecodeError:
        return NEGATIVE
    if not isinstance(data, dict):
        return NEGATIVE
    devops = data.get("devops")
    if devops is not True:
        return NEGATIVE
    topic = data.get("topic")
    return Verdict(devops=True, topic=topic.strip() if isinstance(topic, str) else "")


class Classifier:
    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    async def classify(self, text: str) -> Verdict:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=CLASSIFY_PROMPT,
                    max_output_tokens=64,
                    # Без цього thinking-токени 2.5 Flash з'їдають ліміт і JSON обрізається
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except Exception:
            logger.exception("Помилка класифікатора")
            return NEGATIVE
        return parse_verdict(response.text or "")
