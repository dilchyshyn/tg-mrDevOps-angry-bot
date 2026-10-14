from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "model"]

MAX_STORED = 2000
MAX_TURNS = 10


@dataclass(frozen=True)
class Turn:
    role: Role
    text: str
    parent_id: int | None


class Dialogs:
    """Ланцюжки reply з ботом у пам'яті, щоб Gemini бачив, що бот уже казав.

    Telegram віддає лише одне повідомлення, на яке відповіли, без решти ланцюжка,
    тому кожну репліку зберігаємо з id батька і йдемо вгору по reply.
    """

    def __init__(self, max_stored: int = MAX_STORED) -> None:
        self._max_stored = max_stored
        self._turns: OrderedDict[tuple[int, int], Turn] = OrderedDict()

    def add(
        self, chat_id: int, message_id: int, role: Role, text: str, parent_id: int | None = None
    ) -> None:
        self._turns[(chat_id, message_id)] = Turn(role, text, parent_id)
        self._turns.move_to_end((chat_id, message_id))
        while len(self._turns) > self._max_stored:
            self._turns.popitem(last=False)

    def thread(self, chat_id: int, message_id: int, limit: int = MAX_TURNS) -> list[Turn]:
        """Репліки від початку ланцюжка до `message_id` включно, не більше `limit` останніх."""
        turns: list[Turn] = []
        current: int | None = message_id
        while current is not None and len(turns) < limit:
            turn = self._turns.get((chat_id, current))
            if turn is None:
                break
            turns.append(turn)
            current = turn.parent_id
        turns.reverse()
        return turns
