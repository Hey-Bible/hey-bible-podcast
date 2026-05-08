#!/usr/bin/env python3
"""Verify all verses are present and identify gaps"""

import json
import os
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER

BASE_DIR = Path(__file__).parent.parent
VERSES_DIR = BASE_DIR / "verses"

def get_existing_verses():
    """Get all existing verse files"""
    existing = set()
    verse_pattern = re.compile(r'^(.+)-(\d+)-(\d+)-web$')  # book-chapter-verse-web
    
    for book_dir in VERSES_DIR.iterdir():
        if not book_dir.is_dir():
            continue
        book = book_dir.name
        for chapter_dir in book_dir.iterdir():
            if not chapter_dir.is_dir():
                continue
            chapter = chapter_dir.name
            for verse_file in chapter_dir.glob("*.mp3"):
                match = verse_pattern.match(verse_file.stem)
                if match:
                    file_book, file_chapter, verse = match.groups()
                    existing.add(f"{file_book}-{file_chapter}-{verse}")
                else:
                    print(f"  Warning: Could not parse {verse_file.name}")
    return existing

def get_expected_verses():
    """Get all verses that should exist based on Bible structure"""
    expected = set()
    for book in BOOK_ORDER:
        chapters = BIBLE_STRUCTURE[book]["chapters"]
        for chapter_idx, verse_count in enumerate(chapters):
            chapter = chapter_idx + 1
            for verse in range(1, verse_count + 1):
                expected.add(f"{book}-{chapter}-{verse}")
    return expected

def check_book(book_name):
    """Check specific book for gaps"""
    chapters = BIBLE_STRUCTURE[book_name]["chapters"]
    book_dir = VERSES_DIR / book_name
    
    missing = []
    for chapter_idx, verse_count in enumerate(chapters):
        chapter = chapter_idx + 1
        chapter_dir = book_dir / str(chapter)
        
        for verse in range(1, verse_count + 1):
            verse_file = chapter_dir / f"{book_name}-{chapter}-{verse}-web.mp3"
            if not verse_file.exists():
                missing.append(f"{book_name}-{chapter}-{verse}")
    
    return missing

def main():
    print("Verifying Bible verse files...")
    print("=" * 50)
    
    existing = get_existing_verses()
    expected = get_expected_verses()
    
    total_expected = len(expected)
    total_existing = len(existing)
    
    print(f"Total verses expected: {total_expected:,}")
    print(f"Total verses existing: {total_existing:,}")
    print(f"Completion: {total_existing/total_expected*100:.2f}%")
    print()
    
    missing = expected - existing
    
    if missing:
        print(f"⚠️  Missing {len(missing)} verses!")
        
        # Group by book
        by_book = {}
        for v in missing:
            book = v.split("-", 1)[0]  # Get book name (handles 1-samuel, 2-kings, etc.)
            # Handle numbered books
            if v.startswith('1-') or v.startswith('2-'):
                book = v.rsplit("-", 2)[0]  # Get "1-samuel", "2-kings", etc.
            else:
                book = v.split("-", 1)[0]  # Get "genesis", "exodus", etc.
            by_book.setdefault(book, []).append(v)
        
        print("\nMissing verses by book:")
        # Sort by book order
        book_order_map = {b: i for i, b in enumerate(BOOK_ORDER)}
        sorted_books = sorted(by_book.keys(), key=lambda b: book_order_map.get(b, 999))
        
        for book in sorted_books:
            book_missing = sorted(by_book[book], key=lambda x: (int(x.rsplit("-", 2)[1]), int(x.rsplit("-", 2)[2])))
            print(f"\n  {book}: {len(book_missing)} missing")
            # Show first 10
            for v in book_missing[:10]:
                print(f"    - {v}")
            if len(book_missing) > 10:
                print(f"    ... and {len(book_missing) - 10} more")
    else:
        print("✅ All verses present!")
    
    # Check specific completed books
    print("\n" + "=" * 50)
    print("Checking books up to current progress for gaps...")
    
    # Get books in progress
    books_to_check = ["genesis", "exodus", "leviticus", "numbers", "deuteronomy"]
    for book in books_to_check:
        missing = check_book(book)
        if missing:
            print(f"\n  ⚠️  {book.upper()}: {len(missing)} missing verses")
            for v in missing[:10]:
                print(f"      - {v}")
            if len(missing) > 10:
                print(f"      ... and {len(missing) - 10} more")
        else:
            print(f"  ✅ {book.upper()}: Complete")

if __name__ == "__main__":
    main()
