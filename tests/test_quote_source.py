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


async def test_static_mode_returns_none_when_exhausted() -> None:
    source = QuoteSource(_quotes(2), mode="static", client=None, model="m", rng=random.Random(0))
    assert await source.next_quote("docker") is not None
    assert await source.next_quote("docker") is not None
    assert await source.next_quote("docker") is None


async def test_mixed_mode_without_client_returns_none_after_pool() -> None:
    source = QuoteSource(_quotes(1), mode="mixed", client=None, model="m", rng=random.Random(0))
    assert await source.next_quote("") == "t0"
    assert await source.next_quote("") is None


async def test_generate_mode_without_client_returns_none() -> None:
    source = QuoteSource(_quotes(3), mode="generate", client=None, model="m")
    assert await source.next_quote("k8s") is None


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
