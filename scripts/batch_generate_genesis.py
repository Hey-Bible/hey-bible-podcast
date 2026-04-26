#!/usr/bin/env python3
"""Batch generate ALL missing Genesis verses using Venice TTS"""

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
STATE_DIR = BASE_DIR / "state"
PROGRESS_FILE = STATE_DIR / "genesis_batch_progress.json"

# TTS Configuration
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"

# Genesis chapter verse counts
GENESIS_CHAPTERS = BIBLE_STRUCTURE["genesis"]["chapters"]

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
            key = data.get("skills", {}).get("entries", {}).get("venice-ai-media", {}).get("env", {}).get("VENICE_API_KEY", "")
            if key:
                return key
        except:
            pass
    
    raise ValueError("VENICE_API_KEY not found in environment or config")

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
        print(f"  Error fetching {book} {chapter}:{verse}: {e}")
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

def load_progress():
    """Load batch progress"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    
    return {
        "completed_chapters": [],
        "total_generated": 0,
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def save_progress(progress):
    """Save batch progress"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_existing_verses(chapter: int) -> set:
    """Get set of existing verse numbers for a chapter"""
    chapter_dir = BOOKS_DIR / "genesis" / str(chapter)
    if not chapter_dir.exists():
        return set()
    
    existing = set()
    for f in chapter_dir.glob("*.mp3"):
        try:
            verse = int(f.stem.split("-")[-2])
            existing.add(verse)
        except:
            pass
    return existing

def commit_chapters(start_ch: int, end_ch: int, count: int):
    """Commit and push generated verses"""
    try:
        os.chdir(BASE_DIR)
        
        # Add new files
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        # Check if there are changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode != 0:
            commit_msg = f"Regenerate Genesis verses: chapters {start_ch}-{end_ch} ({count} new verses)"
            
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
            
    except subprocess.CalledProcessError as e:
        print(f"  Git error: {e}")
        return False
    except Exception as e:
        print(f"  Git error: {e}")
        return False
    
    return False

def generate_chapter(chapter: int, api_key: str, progress: dict) -> int:
    """Generate all missing verses for a chapter"""
    expected_verses = GENESIS_CHAPTERS[chapter - 1]
    existing = get_existing_verses(chapter)
    missing = set(range(1, expected_verses + 1)) - existing
    
    if not missing:
        print(f"Chapter {chapter}: Complete ({expected_verses}/{expected_verses} verses)")
        if chapter not in progress["completed_chapters"]:
            progress["completed_chapters"].append(chapter)
        return 0
    
    print(f"\n{'='*60}")
    print(f"Chapter {chapter}: Generating {len(missing)}/{expected_verses} missing verses")
    print(f"Missing verses: {sorted(missing)}")
    print(f"{'='*60}")
    
    generated = 0
    failed = []
    
    for verse in sorted(missing):
        output_dir = BOOKS_DIR / "genesis" / str(chapter)
        filename = f"genesis-{chapter}-{verse}-{TRANSLATION}.mp3"
        output_path = output_dir / filename
        
        # Skip if exists (double check)
        if output_path.exists():
            print(f"  [{verse}] Already exists, skipping")
            generated += 1
            continue
        
        # Fetch verse text
        verse_text = get_verse_text("genesis", chapter, verse)
        if not verse_text:
            print(f"  [{verse}] ✗ Failed to fetch text")
            failed.append(verse)
            continue
        
        print(f"  [{verse}/{expected_verses}] {verse_text[:60]}...")
        
        # Generate TTS
        if generate_tts(verse_text, output_path, api_key):
            print(f"  [{verse}] ✓ Generated")
            generated += 1
            progress["total_generated"] += 1
            time.sleep(0.3)  # Small delay between requests
        else:
            print(f"  [{verse}] ✗ Failed to generate")
            failed.append(verse)
    
    print(f"\nChapter {chapter} complete: {generated}/{len(missing)} generated")
    if failed:
        print(f"  Failed verses: {failed}")
    
    # Mark chapter complete if all verses exist now
    existing_after = get_existing_verses(chapter)
    if len(existing_after) >= expected_verses:
        if chapter not in progress["completed_chapters"]:
            progress["completed_chapters"].append(chapter)
            print(f"  ✓ Chapter {chapter} marked complete")
    
    save_progress(progress)
    return generated

def main():
    """Main batch generation"""
    
    print("="*60)
    print("GENESIS BATCH VERSE GENERATION")
    print("="*60)
    print()
    
    # Get API key
    try:
        api_key = get_api_key()
        print(f"API key loaded: {api_key[:10]}...")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Load progress
    progress = load_progress()
    print(f"Previously completed chapters: {progress.get('completed_chapters', [])}")
    print(f"Total previously generated: {progress.get('total_generated', 0)}")
    print()
    
    # Process all chapters 2-50 (chapter 1 is complete)
    chapters_to_process = list(range(2, 51))
    
    total_new = 0
    commit_start_ch = None
    commit_count = 0
    
    for chapter in chapters_to_process:
        # Track commit batch
        if commit_start_ch is None:
            commit_start_ch = chapter
        
        # Generate chapter
        new_verses = generate_chapter(chapter, api_key, progress)
        total_new += new_verses
        commit_count += new_verses
        
        # Commit every 5 chapters
        if chapter % 5 == 0 and commit_count > 0:
            print(f"\n--- Committing chapters {commit_start_ch}-{chapter} ---")
            commit_chapters(commit_start_ch, chapter, commit_count)
            commit_start_ch = None
            commit_count = 0
        
        # Report progress every 10 chapters
        if chapter % 10 == 0:
            print(f"\n{'#'*60}")
            print(f"PROGRESS REPORT: Completed chapters through {chapter}")
            print(f"Total verses generated this run: {total_new}")
            print(f"Total verses overall: {progress['total_generated']}")
            print(f"Completed chapters: {len(progress['completed_chapters'])}/50")
            print(f"{'#'*60}\n")
    
    # Final commit if needed
    if commit_count > 0 and commit_start_ch:
        print(f"\n--- Final commit: chapters {commit_start_ch}-50 ---")
        commit_chapters(commit_start_ch, 50, commit_count)
    
    print()
    print("="*60)
    print("BATCH GENERATION COMPLETE")
    print("="*60)
    print(f"Total new verses generated: {total_new}")
    print(f"Total verses in project: {progress['total_generated']}")
    print(f"Completed chapters: {len(progress['completed_chapters'])}/50")
    print(f"Progress saved to: {PROGRESS_FILE}")

if __name__ == "__main__":
    main()
