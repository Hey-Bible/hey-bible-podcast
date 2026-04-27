#!/usr/bin/env python3
"""Pre-process the WEB USFX XML into a clean JSON lookup file.

Source: scripts/data/eng-web.usfx.xml (from github.com/seven1m/open-bibles)
Output: scripts/data/web-bible.json

Schema: {"genesis": {"1": {"1": "In the beginning, ..."}}}

Footnotes (<f>) and cross-references (<x>) are stripped entirely. All other
inline tags contribute their text content. Whitespace is normalized so the
output matches what bible-api.com previously returned (single-spaced, trimmed).
"""

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER

BASE_DIR = Path(__file__).parent
XML_PATH = BASE_DIR / "data" / "eng-web.usfx.xml"
JSON_PATH = BASE_DIR / "data" / "web-bible.json"

# USFM 3-letter book ID -> our lowercase-hyphenated book name.
USFM_TO_BOOK = {
    "GEN": "genesis", "EXO": "exodus", "LEV": "leviticus", "NUM": "numbers",
    "DEU": "deuteronomy", "JOS": "joshua", "JDG": "judges", "RUT": "ruth",
    "1SA": "1-samuel", "2SA": "2-samuel", "1KI": "1-kings", "2KI": "2-kings",
    "1CH": "1-chronicles", "2CH": "2-chronicles", "EZR": "ezra", "NEH": "nehemiah",
    "EST": "esther", "JOB": "job", "PSA": "psalms", "PRO": "proverbs",
    "ECC": "ecclesiastes", "SNG": "song-of-solomon", "ISA": "isaiah",
    "JER": "jeremiah", "LAM": "lamentations", "EZK": "ezekiel", "DAN": "daniel",
    "HOS": "hosea", "JOL": "joel", "AMO": "amos", "OBA": "obadiah", "JON": "jonah",
    "MIC": "micah", "NAM": "nahum", "HAB": "habakkuk", "ZEP": "zephaniah",
    "HAG": "haggai", "ZEC": "zechariah", "MAL": "malachi",
    "MAT": "matthew", "MRK": "mark", "LUK": "luke", "JHN": "john", "ACT": "acts",
    "ROM": "romans", "1CO": "1-corinthians", "2CO": "2-corinthians",
    "GAL": "galatians", "EPH": "ephesians", "PHP": "philippians",
    "COL": "colossians", "1TH": "1-thessalonians", "2TH": "2-thessalonians",
    "1TI": "1-timothy", "2TI": "2-timothy", "TIT": "titus", "PHM": "philemon",
    "HEB": "hebrews", "JAS": "james", "1PE": "1-peter", "2PE": "2-peter",
    "1JN": "1-john", "2JN": "2-john", "3JN": "3-john", "JUD": "jude",
    "REV": "revelation",
}

# Tags whose entire subtree is dropped (footnotes, cross-references).
DROP_TAGS = {"f", "x"}
# Tags that hold metadata, never spoken.
META_TAGS = {"id", "ide", "h", "toc", "cl", "cp", "vp"}


def normalize(text: str) -> str:
    """Collapse whitespace and trim — match bible-api.com's text shape."""
    return re.sub(r"\s+", " ", text).strip()


def collect_text(elem) -> str:
    """All descendant text of elem, ignoring DROP_TAGS subtrees."""
    if elem.tag in DROP_TAGS:
        return ""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(collect_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def parse_book(book_elem, bible: dict) -> int:
    usfm = book_elem.get("id") or ""
    book_name = USFM_TO_BOOK.get(usfm)
    if not book_name:
        return 0  # Front matter, apocrypha, glossary, etc.

    bible[book_name] = {}
    state = {"chapter": None, "verse": None, "buf": []}
    count = 0

    def flush():
        nonlocal count
        if state["chapter"] is None or state["verse"] is None:
            return
        text = normalize("".join(state["buf"]))
        if not text:
            return
        ch_key = str(state["chapter"])
        v_key = str(state["verse"])
        bible[book_name].setdefault(ch_key, {})
        existing = bible[book_name][ch_key].get(v_key)
        if existing:
            # Verse spans multiple paragraphs — concat.
            bible[book_name][ch_key][v_key] = normalize(existing + " " + text)
        else:
            bible[book_name][ch_key][v_key] = text
            count += 1

    def visit(node):
        for child in node:
            tag = child.tag
            if tag == "c":
                flush()
                state["chapter"] = int(child.get("id") or 0)
                state["verse"] = None
                state["buf"] = []
            elif tag == "v":
                flush()
                vid = child.get("id") or "0"
                state["verse"] = int(vid.split("-")[0])
                state["buf"] = []
                if child.tail:
                    state["buf"].append(child.tail)
            elif tag == "ve":
                flush()
                state["verse"] = None
                state["buf"] = []
            elif tag in DROP_TAGS:
                if child.tail and state["verse"] is not None:
                    state["buf"].append(child.tail)
            elif tag in META_TAGS:
                pass
            else:
                # Container or inline: take its full text if no nested verse
                # boundaries; otherwise descend so boundaries fire correctly.
                has_boundary = any(e.tag in {"c", "v", "ve"} for e in child.iter())
                if has_boundary:
                    if child.text and state["verse"] is not None:
                        state["buf"].append(child.text)
                    visit(child)
                    if child.tail and state["verse"] is not None:
                        state["buf"].append(child.tail)
                else:
                    if state["verse"] is not None:
                        text = collect_text(child)
                        if text:
                            state["buf"].append(text)
                    if child.tail and state["verse"] is not None:
                        state["buf"].append(child.tail)

    visit(book_elem)
    flush()
    return count


def main():
    if not XML_PATH.exists():
        sys.exit(f"Missing source XML at {XML_PATH}")

    print(f"Parsing {XML_PATH} ({XML_PATH.stat().st_size:,} bytes)...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    bible: dict = {}
    total = 0
    for book_elem in root.findall("book"):
        n = parse_book(book_elem, bible)
        if n:
            total += n

    # Compare to bible_data.BIBLE_STRUCTURE — divergences are warnings, not errors,
    # since the XML is now the source of truth (the existing bible_data.py predates this).
    print(f"\nParsed {total:,} verses across {len(bible)} books.")
    print("Comparing against bible_data.BIBLE_STRUCTURE (warnings only)...")
    warnings = []
    for book in BOOK_ORDER:
        expected = BIBLE_STRUCTURE[book]["chapters"]
        got = bible.get(book, {})
        if len(got) != len(expected):
            warnings.append(f"{book}: bible_data has {len(expected)} chapters, XML has {len(got)}")
            continue
        for i, exp_count in enumerate(expected, start=1):
            got_count = len(got.get(str(i), {}))
            if got_count != exp_count:
                warnings.append(
                    f"{book} {i}: bible_data has {exp_count} verses, XML has {got_count}"
                )

    if warnings:
        print(f"\n{len(warnings)} divergence(s) — XML is authoritative:")
        for w in warnings[:30]:
            print(f"  - {w}")
        if len(warnings) > 30:
            print(f"  ... and {len(warnings) - 30} more")

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nWrote {total:,} verses to {JSON_PATH} ({JSON_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
