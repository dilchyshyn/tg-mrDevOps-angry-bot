import random
from pathlib import Path

import pytest

from bot.quote_source import QuoteSource, pick_static
from quotes.loader import Quote, load_quotes

QUOTES_FILE = Path(__file__).resolve().parent.parent / "quotes" / "quotes.yaml"


def _quotes(n: int) -> list[Quote]:
    return [Quote(id=f"q{i}", text=f"t{i}", lang="uk") for i in range(n)]


def test_pick_static_never_repeats_until_exhausted() -> None:
    quotes = _quotes(5)
    used: set[str] = set()
    rng = random.Random(1)
    picked = [pick_static(quotes, used, rng) for _ in range(5)]
    ids = [q.id for q in picked if q is not None]
    assert sorted(ids) == sorted(q.id for q in quotes)
    assert pick_static(quotes, used, rng) is None


async def test_static_mode_cycles_pool_without_repeats_in_round() -> None:
    source = QuoteSource(_quotes(3), mode="static", client=None, model="m", rng=random.Random(0))
    first_round = [await source.next_quote("docker") for _ in range(3)]
    assert sorted(q for q in first_round if q) == ["t0", "t1", "t2"]
    second_round = [await source.next_quote("docker") for _ in range(3)]
    assert sorted(q for q in second_round if q) == ["t0", "t1", "t2"]


def test_pick_static_skips_recent_while_possible() -> None:
    quotes = _quotes(3)
    rng = random.Random(0)
    for _ in range(20):
        quote = pick_static(quotes, set(), rng, recent={"q0", "q1"})
        assert quote is not None and quote.id == "q2"
    # Усі доступні нещодавні: вибір усе одно є
    assert pick_static(quotes, {"q2"}, rng, recent={"q0", "q1"}) is not None


async def test_no_recent_repeat_across_rounds() -> None:
    pool = 30
    window = pool // 3
    for seed in range(50):
        source = QuoteSource(
            _quotes(pool), mode="static", client=None, model="m", rng=random.Random(seed)
        )
        shown = [source.static_quote() for _ in range(pool * 4)]
        for i in range(len(shown)):
            assert shown[i] not in shown[max(0, i - window) : i], (seed, i)


async def test_mixed_mode_without_client_falls_back_to_pool() -> None:
    source = QuoteSource(_quotes(1), mode="mixed", client=None, model="m", rng=random.Random(0))
    assert await source.next_quote("") == "t0"
    assert await source.next_quote("") == "t0"


async def test_generate_mode_without_client_falls_back_to_pool() -> None:
    source = QuoteSource(_quotes(3), mode="generate", client=None, model="m")
    assert await source.next_quote("k8s") in {"t0", "t1", "t2"}


def test_static_quote_on_empty_pool_is_none() -> None:
    source = QuoteSource([], mode="static", client=None, model="m")
    assert source.static_quote() is None


def test_bundled_quotes_file_is_valid() -> None:
    quotes = load_quotes(QUOTES_FILE)
    assert len(quotes) >= 30
    assert len({q.id for q in quotes}) == len(quotes)
    assert all(q.text for q in quotes)


def test_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "q.yaml"
    path.write_text(
        'quotes:\n  - {id: a, text: "x", lang: uk}\n  - {id: a, text: "y", lang: uk}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Дубль id"):
        load_quotes(path)


def test_loader_rejects_unknown_lang(tmp_path: Path) -> None:
    path = tmp_path / "q.yaml"
    path.write_text('quotes:\n  - {id: a, text: "x", lang: en}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Невідома мова"):
        load_quotes(path)


def test_state_survives_restart(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    quotes = _quotes(10)
    first = QuoteSource(quotes, mode="static", client=None, model="m", state_path=state)
    shown = {first.static_quote() for _ in range(6)}

    second = QuoteSource(quotes, mode="static", client=None, model="m", state_path=state)
    rest = {second.static_quote() for _ in range(4)}
    assert shown | rest == {f"t{i}" for i in range(10)}


def test_state_drops_removed_quotes(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text('{"used": ["q0", "gone"], "recent": ["gone", "q0"]}', encoding="utf-8")
    source = QuoteSource(_quotes(2), mode="static", client=None, model="m", state_path=state)
    assert source.static_quote() == "t1"


def test_broken_state_is_ignored(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text("не json", encoding="utf-8")
    source = QuoteSource(_quotes(2), mode="static", client=None, model="m", state_path=state)
    assert source.static_quote() in {"t0", "t1"}
    assert '"used"' in state.read_text(encoding="utf-8")
