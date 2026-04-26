#!/usr/bin/env python3
"""Generate missing Genesis verses for chapters 34-50"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

# Configuration
BASE_DIR = Path(__file__).parent.parent
BOOKS_DIR = BASE_DIR / "verses"
TRANSLATION = "web"
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"

# Chapter verse counts (Genesis 34-50)
CHAPTER_VERSES = {
    34: 31, 35: 29, 36: 43, 37: 36, 38: 30, 39: 23, 40: 23,
    41: 57, 42: 38, 43: 34, 44: 34, 45: 28, 46: 34, 47: 31,
    48: 22, 49: 33, 50: 26
}

def get_api_key():
    """Get Venice API key from environment or config"""
    key = os.environ.get("VENICE_API_KEY", "").strip()
    if key:
        return key
    
    # Try openclaw config
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

def get_verse_text(chapter, verse):
    """Fetch verse text from bible-api.com with retry"""
    url = f"https://bible-api.com/genesis+{chapter}:{verse}?translation={TRANSLATION}"
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WEB-Bible-Audio/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
                text = data.get("text", "").strip()
                return text
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 * (attempt + 1)
                time.sleep(wait)
                continue
            time.sleep(1)
        except Exception as e:
            time.sleep(1)
    
    return None

def generate_tts(text, output_path, api_key):
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
                print(f"  Warning: Response too small ({len(audio_data)} bytes)")
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return True
            
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def get_existing_verses(chapter):
    """Get list of existing verse numbers for a chapter"""
    chapter_dir = BOOKS_DIR / "genesis" / str(chapter)
    existing = []
    
    if not chapter_dir.exists():
        return existing
    
    for f in chapter_dir.glob("*.mp3"):
        try:
            # Extract verse from filename like genesis-34-1-web.mp3
            verse = int(f.stem.split("-")[2])
            existing.append(verse)
        except:
            pass
    
    return sorted(existing)

def git_commit(chapters_done, verses_generated):
    """Commit changes"""
    try:
        os.chdir(BASE_DIR)
        subprocess.run(["git", "add", "verses/genesis/"], check=True, capture_output=True)
        
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode != 0:
            commit_msg = f"Add Genesis verses: chapters {min(chapters_done)}-{max(chapters_done)} (+{verses_generated} verses)"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
            print(f"  Committed: {commit_msg}")
            return True
    except Exception as e:
        print(f"  Git error: {e}")
    return False

def main():
    print("=" * 60)
    print("Genesis Chapters 34-50 Missing Verse Generator")
    print("=" * 60)
    
    # Get API key
    try:
        api_key = get_api_key()
        print(f"API key loaded")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Find missing verses for each chapter
    missing_by_chapter = {}
    total_missing = 0
    
    for chapter, total_verses in CHAPTER_VERSES.items():
        existing = get_existing_verses(chapter)
        all_verses = set(range(1, total_verses + 1))
        existing_set = set(existing)
        missing = sorted(all_verses - existing_set)
        
        if missing:
            missing_by_chapter[chapter] = missing
            total_missing += len(missing)
            print(f"Chapter {chapter}: {len(existing)}/{total_verses} exist, missing {len(missing)} verses")
    
    if total_missing == 0:
        print("\nAll verses already generated!")
        return
    
    print(f"\nTotal missing verses: {total_missing}")
    print(f"Chapters with missing verses: {list(missing_by_chapter.keys())}")
    print()
    
    # Generate verses
    generated = 0
    failed = []
    chapters_completed = []
    
    for chapter, missing_verses in missing_by_chapter.items():
        print(f"\n--- Chapter {chapter} ({len(missing_verses)} verses) ---")
        
        for verse in missing_verses:
            print(f"  {chapter}:{verse} ...", end=" ", flush=True)
            
            # Get verse text
            text = get_verse_text(chapter, verse)
            time.sleep(1.5)  # Delay to avoid bible-api.com rate limits
            
            if not text:
                print("FAILED (no text)")
                failed.append((chapter, verse))
                continue
            
            # Prepare output path
            output_dir = BOOKS_DIR / "genesis" / str(chapter)
            filename = f"genesis-{chapter}-{verse}-web.mp3"
            output_path = output_dir / filename
            
            if output_path.exists():
                print("SKIPPED (exists)")
                generated += 1
                continue
            
            # Generate TTS
            if generate_tts(text, output_path, api_key):
                print("OK")
                generated += 1
                time.sleep(0.5)  # Rate limiting between TTS calls
            else:
                print("FAILED (TTS)")
                failed.append((chapter, verse))
            
            # Longer delay after every 5 verses to avoid rate limits
            if generated % 5 == 0:
                time.sleep(2)
        
        chapters_completed.append(chapter)
        
        # Commit every 5 chapters or at end
        if len(chapters_completed) >= 5 or chapter == max(missing_by_chapter.keys()):
            print(f"\nCommitting chapters {min(chapters_completed)}-{max(chapters_completed)}...")
            git_commit(chapters_completed, generated)
            chapters_completed = []
    
    # Summary
    print()
    print("=" * 60)
    print(f"Summary: {generated}/{total_missing} verses generated")
    if failed:
        print(f"Failed: {len(failed)} verses")
        for ch, v in failed:
            print(f"  {ch}:{v}")
    print("=" * 60)

if __name__ == "__main__":
    main()
