import re
from dataclasses import dataclass, field

from aiogram.types import User


@dataclass(frozen=True)
class ProtectedUsers:
    """Люди, з якими бот не грубить: без цитат з матами, звертання ввічливо."""

    ids: frozenset[int] = field(default_factory=frozenset)
    usernames: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def parse(cls, raw: str) -> "ProtectedUsers":
        """Рядок з `PROTECTED_USERS`: Telegram ID або @username через кому чи пробіл."""
        ids: set[int] = set()
        usernames: set[str] = set()
        for item in re.split(r"[,\s]+", raw):
            item = item.strip().lstrip("@").lower()
            if not item:
                continue
            if item.lstrip("-").isdigit():
                ids.add(int(item))
            else:
                usernames.add(item)
        return cls(frozenset(ids), frozenset(usernames))

    def contains(self, user: User | None) -> bool:
        if user is None:
            return False
        if user.id in self.ids:
            return True
        return user.username is not None and user.username.lower() in self.usernames
