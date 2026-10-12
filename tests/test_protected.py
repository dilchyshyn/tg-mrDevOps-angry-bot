from types import SimpleNamespace
from typing import Any

from bot.protected import ProtectedUsers


def _user(user_id: int, username: str | None) -> Any:
    return SimpleNamespace(id=user_id, username=username)


def test_parse_ids_and_usernames() -> None:
    protected = ProtectedUsers.parse(" @Kate, 123456789  olya ,, -100 ")
    assert protected.ids == {123456789, -100}
    assert protected.usernames == {"kate", "olya"}


def test_parse_empty() -> None:
    assert ProtectedUsers.parse("") == ProtectedUsers()


def test_contains_by_username_case_insensitive() -> None:
    protected = ProtectedUsers.parse("@kate")
    assert protected.contains(_user(1, "KaTe"))
    assert not protected.contains(_user(2, "vasya"))
    assert not protected.contains(_user(3, None))


def test_contains_by_id() -> None:
    protected = ProtectedUsers.parse("42")
    assert protected.contains(_user(42, None))
    assert not protected.contains(None)
