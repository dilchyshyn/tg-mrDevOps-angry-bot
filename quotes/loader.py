from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

Lang = Literal["uk", "surzhyk"]


@dataclass(frozen=True)
class Quote:
    id: str
    text: str
    lang: Lang
    tags: tuple[str, ...] = field(default_factory=tuple)


def load_quotes(path: str | Path) -> list[Quote]:
    """Читає `quotes.yaml` і перевіряє кожну цитату."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    items = raw.get("quotes", [])
    quotes: list[Quote] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        quote_id = str(item.get("id", f"q{index}"))
        if quote_id in seen:
            raise ValueError(f"Дубль id цитати: {quote_id}")
        seen.add(quote_id)
        lang = item.get("lang", "uk")
        if lang not in ("uk", "surzhyk"):
            raise ValueError(f"Невідома мова в цитаті {quote_id}: {lang}")
        quotes.append(
            Quote(
                id=quote_id,
                text=str(item["text"]).strip(),
                lang=lang,
                tags=tuple(item.get("tags", [])),
            )
        )
    return quotes
