#!/usr/bin/env python3
"""Recompile the entire Exodus book"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE

BASE_DIR = Path(__file__).parent.parent
CHAPTERS_DIR = BASE_DIR / "chapters" / "exodus"
CHAPTER_TITLES_DIR = BASE_DIR / "assets" / "titles"
INTERMEDIATE_DIR = BASE_DIR / "intermediate"

BOOK = "exodus"

def get_audio_duration(file_path: Path) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 0.0

def get_api_key():
    import os
    key = os.environ.get("VENICE_API_KEY", "").strip()
    if key:
        return key
    
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            key = data.get("skills", {}).get("entries", {}).get("venice-ai", {}).get("env", {}).get("VENICE_API_KEY", "")
            if key:
                return key
        except:
            pass
    
    raise ValueError("VENICE_API_KEY not found")

def generate_book_title():
    """Generate book title audio using Venice TTS"""
    import urllib.request
    
    title_path = INTERMEDIATE_DIR / f"{BOOK}-title.mp3"
    if title_path.exists():
        print(f"  Book title already exists")
        return title_path
    
    url = "https://api.venice.ai/api/v1/audio/speech"
    payload = {
        "model": "tts-elevenlabs-turbo-v2-5",
        "voice": "Bill",
        "input": "The Book of Exodus",
        "response_format": "mp3"
    }
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            audio_data = response.read()
            if len(audio_data) < 1000:
                print("  Warning: Title response too small")
                return None
            with open(title_path, "wb") as f:
                f.write(audio_data)
            print(f"  ✓ Generated book title")
            return title_path
    except Exception as e:
        print(f"  Error generating title: {e}")
        return None

print("=" * 60)
print("Recompiling Exodus Book")
print("=" * 60)

INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

# Remove old intermediate files
old_mp3 = INTERMEDIATE_DIR / f"{BOOK}-web.mp3"
old_json = INTERMEDIATE_DIR / f"{BOOK}-web.json"
old_mp3.unlink(missing_ok=True)
old_json.unlink(missing_ok=True)

# Get chapters
chapters = sorted(
    [f for f in CHAPTERS_DIR.glob("*.mp3") if f.name.startswith(f"{BOOK}-")],
    key=lambda p: int(p.stem.split("-")[1])
)

print(f"Found {len(chapters)} chapters")

# Generate book title
title_path = generate_book_title()
if not title_path:
    print("Failed to generate title")
    sys.exit(1)

# Build concat list
concat_list_path = INTERMEDIATE_DIR / f"{BOOK}-concat.txt"
with open(concat_list_path, "w") as f:
    escaped_title = str(title_path).replace("'", "'\\''")
    f.write(f"file '{escaped_title}'\n")
    
    for chapter_file in chapters:
        chapter_num = int(chapter_file.stem.split("-")[1])
        chapter_title_file = CHAPTER_TITLES_DIR / f"chapter-{chapter_num}.mp3"
        if chapter_title_file.exists():
            escaped_chapter = str(chapter_file).replace("'", "'\\''")
            escaped_chapter_title = str(chapter_title_file).replace("'", "'\\''")
            f.write(f"file '{escaped_chapter_title}'\n")
            f.write(f"file '{escaped_chapter}'\n")

print(f"Stitching {len(chapters)} chapters with titles...")

# Run ffmpeg
output_path = INTERMEDIATE_DIR / f"{BOOK}-web.mp3"
cmd = [
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", str(concat_list_path),
    "-acodec", "copy",
    str(output_path)
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
concat_list_path.unlink(missing_ok=True)

if result.returncode != 0:
    print(f"FFmpeg error: {result.stderr[:500]}")
    sys.exit(1)

if output_path.exists() and output_path.stat().st_size > 10000:
    print(f"✓ Created: {output_path}")
    print(f"  Size: {output_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Build chapter timestamps
    chapter_data = []
    current_offset = get_audio_duration(title_path)
    
    for chapter_file in chapters:
        chapter_num = int(chapter_file.stem.split("-")[1])
        chapter_title_file = CHAPTER_TITLES_DIR / f"chapter-{chapter_num}.mp3"
        if chapter_title_file.exists():
            title_duration = get_audio_duration(chapter_title_file)
            chapter_duration = get_audio_duration(chapter_file)
            chapter_start = current_offset
            current_offset += title_duration + chapter_duration
            chapter_data.append({
                "number": chapter_num,
                "title": f"Chapter {chapter_num}",
                "start": chapter_start,
                "end": current_offset,
                "duration": title_duration + chapter_duration
            })
    
    total_duration = get_audio_duration(output_path)
    chapters_json_path = INTERMEDIATE_DIR / f"{BOOK}-web.json"
    
    chapters_data = {
        "book": BOOK,
        "title": "Exodus",
        "duration": total_duration,
        "chapters": chapter_data
    }
    
    with open(chapters_json_path, "w") as f:
        json.dump(chapters_data, f, indent=2)
    
    print(f"✓ Created: {chapters_json_path}")
    print(f"  Total duration: {total_duration/60:.2f} min")
    print(f"  Tracked {len(chapter_data)} chapters")
    print()
    print("=" * 60)
    print("✓ Exodus book compiled successfully!")
    print("=" * 60)
else:
    print("Output file too small or missing")
    sys.exit(1)
