#!/usr/bin/env python3
"""Regenerate missing individual verse MP3 files for Genesis chapters"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE

# Configuration
BASE_DIR = Path(__file__).parent.parent
BOOKS_DIR = BASE_DIR / "books"
CHAPTERS_DIR = BASE_DIR / "chapters"
STATE_DIR = BASE_DIR / "state"
STATE_FILE = STATE_DIR / "progress.json"

TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"

# Rate limiting
TTS_DELAY = 0.5
RETRY_DELAY = 5
MAX_RETRIES = 3

# Missing chapters to regenerate
MISSING_CHAPTERS = [
    # Genesis 3-17 (15 chapters)
    3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    # Genesis 19-28 (10 chapters)
    19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
    # Genesis 30-31 (2 chapters)
    30, 31,
    # Genesis 33-38 (6 chapters)
    33, 34, 35, 36, 37, 38,
]

BOOK = "genesis"

def get_api_key():
    """Get Venice API key from environment or config"""
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

def get_verse_text(book: str, chapter: int, verse: int) -> str:
    """Fetch verse text from bible-api.com"""
    book_api = book.replace("-", "+")
    url = f"https://bible-api.com/{book_api}+{chapter}:{verse}?translation={TRANSLATION}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WEB-Bible-Audio/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("text", "").strip()
    except Exception as e:
        print(f"  Error fetching {book} {chapter}:{verse}: {e}")
        return None

def generate_tts(text: str, output_path: Path, api_key: str, retries=0) -> bool:
    """Generate TTS using Venice API with retry logic"""
    url = "https://api.venice.ai/api/v1/audio/speech"
    
    payload = {
        "model": TTS_MODEL,
        "voice": TTS_VOICE,
        "input": text,
        "response_format": "mp3"
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            audio_data = response.read()
            
            if len(audio_data) < 1000:
                print(f"  Warning: Response too small ({len(audio_data)} bytes)")
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            return True
            
    except urllib.error.HTTPError as e:
        if e.code == 429 and retries < MAX_RETRIES:
            print(f"  Rate limited, waiting {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY * (retries + 1))
            return generate_tts(text, output_path, api_key, retries + 1)
        print(f"  HTTP Error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def get_chapter_verse_count(book: str, chapter: int) -> int:
    """Get total verses in a chapter"""
    return BIBLE_STRUCTURE[book]["chapters"][chapter - 1]

def git_commit(message):
    """Commit changes to git"""
    try:
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
            print(f"  Committed: {message}")
            return True
    except Exception as e:
        print(f"  Git error: {e}")
    return False

def main():
    print("=" * 60)
    print("Regenerating Missing Genesis Verse MP3s")
    print("=" * 60)
    print(f"Chapters to regenerate: {MISSING_CHAPTERS}")
    print(f"Total chapters: {len(MISSING_CHAPTERS)}")
    print()
    
    try:
        api_key = get_api_key()
        print(f"API key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Calculate total verses to generate
    total_verses = sum(get_chapter_verse_count(BOOK, ch) for ch in MISSING_CHAPTERS)
    print(f"Total verses to generate: {total_verses}")
    print()
    
    generated_count = 0
    failed_verses = []
    chapters_completed = 0
    
    for chapter_num in MISSING_CHAPTERS:
        verse_count = get_chapter_verse_count(BOOK, chapter_num)
        chapter_dir = BOOKS_DIR / BOOK / str(chapter_num)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[Chapter {chapter_num}] Generating {verse_count} verses...")
        
        chapter_generated = 0
        chapter_failed = []
        
        for verse_num in range(1, verse_count + 1):
            verse_file = chapter_dir / f"{BOOK}-{chapter_num}-{verse_num}-{TRANSLATION}.mp3"
            
            # Skip if already exists
            if verse_file.exists():
                chapter_generated += 1
                generated_count += 1
                continue
            
            # Fetch verse text
            verse_text = get_verse_text(BOOK, chapter_num, verse_num)
            if not verse_text:
                print(f"  Failed to fetch Gen {chapter_num}:{verse_num}")
                chapter_failed.append((chapter_num, verse_num))
                failed_verses.append((chapter_num, verse_num))
                continue
            
            # Generate TTS
            print(f"  Gen {chapter_num}:{verse_num} - {verse_text[:50]}...")
            
            if generate_tts(verse_text, verse_file, api_key):
                chapter_generated += 1
                generated_count += 1
                time.sleep(TTS_DELAY)
            else:
                print(f"    ✗ Failed to generate")
                chapter_failed.append((chapter_num, verse_num))
                failed_verses.append((chapter_num, verse_num))
                time.sleep(RETRY_DELAY)
        
        print(f"  Chapter {chapter_num} complete: {chapter_generated}/{verse_count} verses generated")
        chapters_completed += 1
        
        # Commit every 5 chapters
        if chapters_completed % 5 == 0:
            print(f"\n--- Committing progress ({chapters_completed} chapters complete) ---")
            git_commit(f"Regenerate Genesis verses: chapters {MISSING_CHAPTERS[chapters_completed-5]}-{chapter_num}")
    
    # Final commit
    if chapters_completed > 0:
        print(f"\n--- Final commit ---")
        git_commit(f"Regenerate all missing Genesis verse files ({len(MISSING_CHAPTERS)} chapters)")
    
    # Summary
    print()
    print("=" * 60)
    print("REGENERATION COMPLETE")
    print("=" * 60)
    print(f"Chapters processed: {chapters_completed}")
    print(f"Verses generated: {generated_count}/{total_verses}")
    print(f"Failed: {len(failed_verses)}")
    
    if failed_verses:
        print(f"\nFailed verses:")
        for ch, v in failed_verses[:20]:
            print(f"  - Genesis {ch}:{v}")
        if len(failed_verses) > 20:
            print(f"  ... and {len(failed_verses) - 20} more")

if __name__ == "__main__":
    main()
