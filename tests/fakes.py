from types import SimpleNamespace
from typing import Any


class FakeGeminiClient:
    """Імітує `genai.Client`: мокається ланцюжок `aio.models.generate_content`.

    `result` — текст відповіді або виняток, який кине виклик. Аргументи викликів у `calls`.
    """

    def __init__(self, result: str | Exception) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=self._generate))

    async def _generate(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return SimpleNamespace(text=self._result)
