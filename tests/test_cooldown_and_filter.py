from bot.cooldown import Cooldown
from bot.handlers import should_classify


def test_cooldown_blocks_within_window() -> None:
    now = [0.0]
    cooldown = Cooldown(60, clock=lambda: now[0])
    assert cooldown.ready(1)
    cooldown.mark(1)
    now[0] = 59.9
    assert not cooldown.ready(1)
    now[0] = 60.0
    assert cooldown.ready(1)


def test_cooldown_is_per_chat() -> None:
    cooldown = Cooldown(60, clock=lambda: 0.0)
    cooldown.mark(1)
    assert not cooldown.ready(1)
    assert cooldown.ready(2)


def test_should_classify_skips_short_and_non_letter_text() -> None:
    assert not should_classify("ок", 8)
    assert not should_classify("12345 67890", 8)
    assert not should_classify("   ", 8)
    assert should_classify("у нас знову впав docker", 8)
