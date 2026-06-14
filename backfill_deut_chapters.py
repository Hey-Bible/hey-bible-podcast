#!/usr/bin/env python3
"""One-time backfill: stitch Deuteronomy chapter MP3s from individual verses (for compile-book.py)."""

import json
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from bible_data import BIBLE_STRUCTURE

BASE = Path(__file__).parent
VERSES_DIR = BASE / "verses"
CHAPTERS_DIR = BASE / "chapters"
book = "deuteronomy"

chapters = BIBLE_STRUCTURE[book]["chapters"]
total_verses = sum(chapters)
print(f"Backfilling {book} ({len(chapters)} chapters, {total_verses} verses total) from verses/...")

success = 0
for ch_num, verse_count in enumerate(chapters, 1):
    chapter_dir = VERSES_DIR / book / str(ch_num)
    out_dir = CHAPTERS_DIR / book
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book}-{ch_num}-web.mp3"
    
    if out_path.exists():
        print(f"  Ch {ch_num}: already exists, skip")
        success += 1
        continue
    
    if not chapter_dir.exists():
        print(f"  Ch {ch_num}: no verse dir, skip")
        continue
    
    verse_files = sorted(
        chapter_dir.glob("*.mp3"),
        key=lambda p: int(p.stem.split("-")[-2])
    )
    if len(verse_files) < verse_count:
        print(f"  Ch {ch_num}: incomplete ({len(verse_files)}/{verse_count} verses) - skipping")
        continue
    
    print(f"  Ch {ch_num}: stitching {len(verse_files)} verses... ", end="", flush=True)
    
    concat_list = out_dir / f"concat-{ch_num}.txt"
    with open(concat_list, "w") as f:
        for vf in verse_files:
            escaped = str(vf).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-acodec", "copy",
        str(out_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    concat_list.unlink(missing_ok=True)
    
    if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1000:
        print("✓")
        success += 1
    else:
        print(f"✗ {result.stderr[:120] if result.stderr else 'fail'}")
        if out_path.exists():
            out_path.unlink(missing_ok=True)

print(f"\nBackfill complete: {success}/{len(chapters)} chapters ready in chapters/{book}/")
print("You can now run compile-book.py for Deuteronomy.")