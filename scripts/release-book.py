#!/usr/bin/env python3
"""Release compiled book: upload to Cloudflare R2, patch web data, commit."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BOOK_ORDER
import r2

# Paths
BASE_DIR = Path(__file__).parent.parent
INTERMEDIATE_DIR = BASE_DIR / "intermediate"
STATE_FILE = BASE_DIR / "state" / "progress.json"
WEB_DATA_DIR = BASE_DIR / "web" / "src" / "data"
BOOKS_JSON_FILE = WEB_DATA_DIR / "books.json"


def load_progress():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"book": "genesis", "chapter": 1, "verse": 1, "released_books": []}


def save_progress(progress):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def get_book_title(book: str) -> str:
    return book.replace("-", " ").title()


def get_next_book(book: str) -> str | None:
    try:
        idx = BOOK_ORDER.index(book)
        if idx < len(BOOK_ORDER) - 1:
            return BOOK_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def update_book_metadata(book: str, status: str, release_tag: str | None, release_size: int | None):
    """Update a book's status, release tag, and release size in books.json."""
    if not BOOKS_JSON_FILE.exists():
        print(f"  Error: {BOOKS_JSON_FILE} not found")
        return

    with open(BOOKS_JSON_FILE) as f:
        books = json.load(f)

    for b in books:
        if b["slug"] == book:
            b["status"] = status
            b["releaseTag"] = release_tag
            b["releaseSize"] = release_size
            if status == "available":
                b.pop("progress", None)
            break

    with open(BOOKS_JSON_FILE, "w") as f:
        json.dump(books, f, indent=2)

    print(f"  ✓ Updated {book} status to '{status}'")


def release_book(book: str) -> bool:
    """Upload to R2, then patch books.json."""
    print(f"\nReleasing book: {book.title()}")
    print("=" * 60)

    mp3_file = INTERMEDIATE_DIR / f"{book}-complete.mp3"
    json_file = INTERMEDIATE_DIR / f"{book}-chapters.json"

    if not mp3_file.exists():
        print(f"  Error: Intermediate file not found: {mp3_file}")
        print(f"  Run compile-book.py first on the 25th!")
        return False

    if not r2.upload(mp3_file, json_file):
        return False

    release_tag = f"{book}-{datetime.now().strftime('%Y-%m')}"
    release_size = mp3_file.stat().st_size
    update_book_metadata(book, "available", release_tag, release_size)

    return True


def git_commit_release(book: str) -> bool:
    try:
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )

        if result.returncode != 0:
            commit_msg = f"Release: {get_book_title(book)}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["git", "push", "origin", "master"],
                check=True, capture_output=True,
            )
            print(f"  Committed and pushed: {commit_msg}")
            return True
    except Exception as e:
        print(f"  Git error: {e}")
        return False

    return False


def advance_to_next_book(progress, current_book: str):
    next_book = get_next_book(current_book)

    if next_book:
        progress["book"] = next_book
        progress["chapter"] = 1
        progress["verse"] = 1
        if "released_books" not in progress:
            progress["released_books"] = []
        progress["released_books"].append(current_book)
        save_progress(progress)
        print(f"\n✓ Advanced to next book: {next_book.title()}")
    else:
        print(f"\n🎉 END OF BIBLE REACHED!")
        progress["completed"] = True
        save_progress(progress)


def main():
    print("=" * 60)
    print("WEB Bible Book Release")
    print("=" * 60)
    print()

    progress = load_progress()
    current_book = progress["book"]
    released_books = progress.get("released_books", [])

    print(f"Current book: {current_book.title()}")
    print(f"Previously released: {len(released_books)} books")
    if released_books:
        print(f"  {', '.join(b.title() for b in released_books)}")
    print()

    intermediate_file = INTERMEDIATE_DIR / f"{current_book}-complete.mp3"

    if not intermediate_file.exists():
        print(f"No intermediate file found for {current_book.title()}")
        print(f"The book may not be complete yet, or compile-book.py hasn't run.")
        return

    if current_book in released_books:
        print(f"Book '{current_book.title()}' is already released.")
        return

    if release_book(current_book):
        print()
        print("Committing release...")
        git_commit_release(current_book)

        print()
        print("Advancing to next book...")
        advance_to_next_book(progress, current_book)

        print()
        print("=" * 60)
        print(f"✓ SUCCESSFULLY RELEASED: {get_book_title(current_book)}")
        print("=" * 60)
        r2.print_review_links(current_book, include_site=True)
    else:
        print(f"\n✗ Failed to release book '{current_book}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
