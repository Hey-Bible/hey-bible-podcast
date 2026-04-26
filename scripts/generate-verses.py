#!/usr/bin/env python3
"""Generate WEB Bible audio verses using Venice TTS (ElevenLabs Bill voice)"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import urllib.request
import urllib.error

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER, get_next_book_chapter_verse

# Configuration
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
BOOKS_DIR = BASE_DIR / "books"
STATE_FILE = STATE_DIR / "progress.json"

# TTS Configuration
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"
DAILY_BATCH_SIZE = 50  # verses per day

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
    
    raise ValueError("VENICE_API_KEY not found in environment or config")

def get_verse_text(book: str, chapter: int, verse: int) -> str:
    """Fetch verse text from bible-api.com"""
    # Convert book name to API format (spaces become + for URL)
    book_api = book.replace("-", "+")
    
    # Build URL with proper encoding
    url = f"https://bible-api.com/{book_api}+{chapter}:{verse}?translation={TRANSLATION}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WEB-Bible-Audio/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            text = data.get("text", "").strip()
            # Clean up the text (remove verse numbers if present)
            return text
    except Exception as e:
        print(f"Error fetching {book} {chapter}:{verse}: {e}")
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
            
            # Verify it's not an error response
            if len(audio_data) < 1000:
                print(f"  Warning: Response too small ({len(audio_data)} bytes), may be error")
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
    """Load current progress from state file"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    
    # Default: start at Genesis 1:1
    return {
        "book": "genesis",
        "chapter": 1,
        "verse": 1,
        "completed_count": 0,
        "last_run": None
    }

def save_progress(progress):
    """Save progress to state file"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def git_commit_changes(book: str, chapter: int, count: int):
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
        
        if result.returncode != 0:  # There are changes
            # Commit
            commit_msg = f"Add {count} verses: {book.title()} {chapter}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True
            )
            
            # Push
            subprocess.run(
                ["git", "push", "origin", "main"],
                check=True,
                capture_output=True
            )
            
            print(f"  Committed and pushed: {commit_msg}")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"  Git error: {e}")
        return False
    except Exception as e:
        print(f"  Git error: {e}")
        return False
    
    return False

def generate_filename(book: str, chapter: int, verse: int) -> str:
    """Generate filename in format: book-chapter-verse-web.mp3"""
    return f"{book}-{chapter}-{verse}-{TRANSLATION}.mp3"

def main():
    """Main generation loop"""
    
    print("=" * 60)
    print("WEB Bible Audio Generator")
    print("Voice: ElevenLabs Bill via Venice TTS")
    print("=" * 60)
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
    current_book = progress["book"]
    current_chapter = progress["chapter"]
    current_verse = progress["verse"]
    completed_count = progress.get("completed_count", 0)
    
    print(f"Starting from: {current_book.title()} {current_chapter}:{current_verse}")
    print(f"Previously completed: {completed_count} verses")
    print(f"Daily batch size: {DAILY_BATCH_SIZE} verses")
    print()
    
    generated = []
    failed = []
    
    for i in range(DAILY_BATCH_SIZE):
        print(f"[{i+1}/{DAILY_BATCH_SIZE}] {current_book.title()} {current_chapter}:{current_verse}")
        
        # Get verse text
        verse_text = get_verse_text(current_book, current_chapter, current_verse)
        if not verse_text:
            print(f"  Failed to fetch text, skipping...")
            failed.append((current_book, current_chapter, current_verse))
            
            # Move to next verse anyway
            next_book, next_chapter, next_verse = get_next_book_chapter_verse(
                current_book, current_chapter, current_verse
            )
            
            if next_book is None:
                print("\nReached end of Bible!")
                break
            
            current_book, current_chapter, current_verse = next_book, next_chapter, next_verse
            continue
        
        # Prepare output path
        output_dir = BOOKS_DIR / current_book / str(current_chapter)
        filename = generate_filename(current_book, current_chapter, current_verse)
        output_path = output_dir / filename
        
        # Skip if already exists
        if output_path.exists():
            print(f"  Already exists, skipping")
            generated.append(output_path)
        else:
            # Generate TTS
            print(f"  Text: {verse_text[:60]}...")
            print(f"  Generating audio...")
            
            if generate_tts(verse_text, output_path, api_key):
                print(f"  ✓ Saved: {output_path}")
                generated.append(output_path)
                time.sleep(0.5)  # Brief pause between requests
            else:
                print(f"  ✗ Failed to generate")
                failed.append((current_book, current_chapter, current_verse))
        
        # Move to next verse
        next_book, next_chapter, next_verse = get_next_book_chapter_verse(
            current_book, current_chapter, current_verse
        )
        
        if next_book is None:
            print("\nReached end of Bible!")
            break
        
        current_book, current_chapter, current_verse = next_book, next_chapter, next_verse
    
    # Update and save progress
    progress["book"] = current_book
    progress["chapter"] = current_chapter
    progress["verse"] = current_verse
    progress["completed_count"] = completed_count + len(generated)
    progress["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_progress(progress)
    
    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Generated: {len(generated)} verses")
    print(f"  Failed: {len(failed)} verses")
    print(f"  Total completed: {progress['completed_count']} verses")
    print(f"  Next verse: {current_book.title()} {current_chapter}:{current_verse}")
    
    # Git commit if we generated anything
    if generated:
        print()
        print("Committing changes...")
        git_commit_changes(current_book, current_chapter, len(generated))
    
    print()
    print(f"Progress saved to: {STATE_FILE}")

if __name__ == "__main__":
    main()
