from bot.cooldown import Cooldown


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


def test_zero_cooldown_is_always_ready() -> None:
    cooldown = Cooldown(0, clock=lambda: 5.0)
    cooldown.mark(1)
    assert cooldown.ready(1)
