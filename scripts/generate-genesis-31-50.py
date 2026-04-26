#!/usr/bin/env python3
"""Generate Genesis chapters 31-50 verses using Venice TTS"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE

# Configuration
BASE_DIR = Path(__file__).parent.parent
BOOKS_DIR = BASE_DIR / "books"
TRANSLATION = "web"
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"

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
            text = data.get("text", "").strip()
            return text
    except Exception as e:
        print(f"    Error fetching {book} {chapter}:{verse}: {e}")
        return None

def generate_tts(text: str, output_path: Path, api_key: str) -> bool:
    """Generate TTS using Venice API"""
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
                print(f"    Warning: Response too small ({len(audio_data)} bytes)")
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return True
            
    except urllib.error.HTTPError as e:
        print(f"    HTTP Error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"    Error: {e}")
        return False

def get_existing_verses(chapter: int) -> set:
    """Get set of existing verse numbers for a chapter"""
    chapter_dir = BOOKS_DIR / "genesis" / str(chapter)
    if not chapter_dir.exists():
        return set()
    
    verses = set()
    for f in chapter_dir.glob("*.mp3"):
        try:
            # Extract verse number from filename like genesis-32-5-web.mp3
            verse_num = int(f.stem.split("-")[2])
            verses.add(verse_num)
        except (IndexError, ValueError):
            continue
    return verses

def git_commit(start_chapter: int, end_chapter: int, count: int):
    """Commit and push changes"""
    try:
        os.chdir(BASE_DIR)
        
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode != 0:
            commit_msg = f"Regenerate Genesis verses: chapters {start_chapter}-{end_chapter} ({count} new verses)"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                check=True,
                capture_output=True
            )
            print(f"  ✓ Committed: {commit_msg}")
            return True
    except Exception as e:
        print(f"  Git error: {e}")
        return False
    return False

def generate_chapter(chapter: int, api_key: str) -> int:
    """Generate all missing verses for a chapter. Returns count generated."""
    verse_count = BIBLE_STRUCTURE["genesis"]["chapters"][chapter - 1]
    existing = get_existing_verses(chapter)
    missing = [v for v in range(1, verse_count + 1) if v not in existing]
    
    if not missing:
        print(f"  Chapter {chapter}: Complete ({verse_count}/{verse_count})")
        return 0
    
    print(f"  Chapter {chapter}: {len(existing)}/{verse_count} existing, {len(missing)} missing")
    
    generated = 0
    for verse in missing:
        output_path = BOOKS_DIR / "genesis" / str(chapter) / f"genesis-{chapter}-{verse}-web.mp3"
        
        # Skip if exists (double-check)
        if output_path.exists():
            continue
        
        verse_text = get_verse_text("genesis", chapter, verse)
        if not verse_text:
            print(f"    Failed to fetch Genesis {chapter}:{verse}")
            continue
        
        print(f"    Genesis {chapter}:{verse} - {verse_text[:50]}...")
        
        if generate_tts(verse_text, output_path, api_key):
            generated += 1
            time.sleep(0.3)  # Small delay between requests
        else:
            print(f"    Failed to generate Genesis {chapter}:{verse}")
    
    return generated

def main():
    print("=" * 60)
    print("Genesis Chapters 31-50 Regeneration")
    print("Voice: ElevenLabs Bill via Venice TTS")
    print("=" * 60)
    print()
    
    try:
        api_key = get_api_key()
        print(f"API key loaded: {api_key[:10]}...")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Chapters 31-50
    chapters = list(range(31, 51))
    total_generated = 0
    
    # Process in batches of 5 chapters
    for batch_start in range(31, 51, 5):
        batch_end = min(batch_start + 4, 50)
        batch_chapters = list(range(batch_start, batch_end + 1))
        
        print(f"\n{'='*60}")
        print(f"Batch: Chapters {batch_start}-{batch_end}")
        print(f"{'='*60}")
        
        batch_count = 0
        for chapter in batch_chapters:
            count = generate_chapter(chapter, api_key)
            batch_count += count
        
        total_generated += batch_count
        
        if batch_count > 0:
            print(f"\n  Committing batch {batch_start}-{batch_end} ({batch_count} verses)...")
            git_commit(batch_start, batch_end, batch_count)
        else:
            print(f"\n  No new verses in batch {batch_start}-{batch_end}, skipping commit")
    
    print()
    print("=" * 60)
    print("Final Summary:")
    print(f"  Total verses generated: {total_generated}")
    print("=" * 60)

if __name__ == "__main__":
    main()
