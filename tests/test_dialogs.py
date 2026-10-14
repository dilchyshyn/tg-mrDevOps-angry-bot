from bot.dialogs import Dialogs


def test_thread_follows_reply_chain_in_order() -> None:
    dialogs = Dialogs()
    dialogs.add(1, 10, "user", "питання")
    dialogs.add(1, 11, "model", "відповідь", parent_id=10)
    dialogs.add(1, 12, "user", "уточнення", parent_id=11)
    assert [turn.text for turn in dialogs.thread(1, 12)] == ["питання", "відповідь", "уточнення"]


def test_thread_is_limited_to_last_turns() -> None:
    dialogs = Dialogs()
    dialogs.add(1, 0, "user", "0")
    for i in range(1, 6):
        dialogs.add(1, i, "model" if i % 2 else "user", str(i), parent_id=i - 1)
    assert [turn.text for turn in dialogs.thread(1, 5, limit=3)] == ["3", "4", "5"]


def test_thread_is_per_chat_and_unknown_is_empty() -> None:
    dialogs = Dialogs()
    dialogs.add(1, 10, "user", "питання")
    assert dialogs.thread(2, 10) == []
    assert dialogs.thread(1, 99) == []


def test_oldest_turns_are_evicted() -> None:
    dialogs = Dialogs(max_stored=2)
    dialogs.add(1, 1, "user", "a")
    dialogs.add(1, 2, "model", "b", parent_id=1)
    dialogs.add(1, 3, "user", "c", parent_id=2)
    assert [turn.text for turn in dialogs.thread(1, 3)] == ["b", "c"]
