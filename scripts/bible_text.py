"""Local WEB Bible verse lookup, backed by scripts/data/web-bible.json.

The JSON is produced by build-bible-json.py from the eng-web.usfx.xml file in
github.com/seven1m/open-bibles. Loading is lazy so importing is cheap.
"""

import json
from functools import lru_cache
from pathlib import Path

JSON_PATH = Path(__file__).parent / "data" / "web-bible.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_verse_text(book: str, chapter: int, verse: int) -> str | None:
    """Return the WEB verse text, or None if missing."""
    bible = _load()
    return bible.get(book, {}).get(str(chapter), {}).get(str(verse))
