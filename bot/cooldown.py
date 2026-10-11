import time
from collections.abc import Callable


class Cooldown:
    """Пауза між відповідями окремо для кожного чату."""

    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._seconds = seconds
        self._clock = clock
        self._last: dict[int, float] = {}

    def ready(self, chat_id: int) -> bool:
        last = self._last.get(chat_id)
        return last is None or self._clock() - last >= self._seconds

    def mark(self, chat_id: int) -> None:
        self._last[chat_id] = self._clock()
