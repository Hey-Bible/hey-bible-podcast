#!/usr/bin/env python3
"""Bulk generate complete Book of Genesis for Hey Bible Podcast"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER, get_next_book_chapter_verse

# Configuration
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
BOOKS_DIR = BASE_DIR / "books"
CHAPTERS_DIR = BASE_DIR / "chapters"
INTERMEDIATE_DIR = BASE_DIR / "intermediate"
CHAPTER_TITLES_DIR = BASE_DIR / "assets" / "titles"
STATE_FILE = STATE_DIR / "progress.json"

TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"

# Rate limiting
TTS_DELAY = 0.5  # seconds between TTS requests
RETRY_DELAY = 5  # seconds on rate limit
MAX_RETRIES = 3

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

def load_progress():
    """Load current progress"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"book": "genesis", "chapter": 1, "verse": 1, "completed_count": 0, "completed_chapters": []}

def save_progress(progress):
    """Save progress"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    progress["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_chapter_verse_count(book: str, chapter: int) -> int:
    """Get total verses in a chapter"""
    return BIBLE_STRUCTURE[book]["chapters"][chapter - 1]

def stitch_chapter(book: str, chapter: int) -> bool:
    """Stitch all verses in a chapter into a single MP3"""
    chapter_dir = BOOKS_DIR / book / str(chapter)
    output_dir = CHAPTERS_DIR / book
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{book}-{chapter}-web.mp3"
    
    if output_path.exists():
        return True
    
    verse_files = sorted(
        chapter_dir.glob("*.mp3"),
        key=lambda p: int(p.stem.split("-")[-2])
    )
    
    if not verse_files:
        return False
    
    expected = get_chapter_verse_count(book, chapter)
    if len(verse_files) < expected:
        print(f"  Chapter {chapter} incomplete: {len(verse_files)}/{expected}")
        return False
    
    concat_list = output_dir / f"concat-{chapter}.txt"
    with open(concat_list, "w") as f:
        for vf in verse_files:
            escaped_path = str(vf).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-acodec", "copy",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        concat_list.unlink()
        
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr[:500]}")
            return False
        
        if output_path.exists() and output_path.stat().st_size > 1000:
            for vf in verse_files:
                vf.unlink()
            if chapter_dir.exists() and not any(chapter_dir.iterdir()):
                chapter_dir.rmdir()
            print(f"  ✓ Chapter {chapter} stitched ({len(verse_files)} verses)")
            return True
    except Exception as e:
        print(f"  Stitch error: {e}")
        return False
    return False

def generate_book_title(book: str, api_key: str) -> Path:
    """Generate book title audio"""
    title_path = INTERMEDIATE_DIR / f"{book}-title.mp3"
    if title_path.exists():
        return title_path
    
    book_display = book.replace("-", " ").title()
    text = f"The Book of {book_display}"
    
    print(f"Generating book title: '{text}'")
    if generate_tts(text, title_path, api_key):
        print(f"  ✓ Book title generated")
        return title_path
    return None

def compile_full_book(book: str) -> bool:
    """Compile all chapters into complete book MP3"""
    print(f"\n{'='*60}")
    print(f"Compiling complete Book of {book.title()}")
    print(f"{'='*60}")
    
    chapters_dir = CHAPTERS_DIR / book
    if not chapters_dir.exists():
        print(f"No chapters directory found")
        return False
    
    expected_chapters = len(BIBLE_STRUCTURE[book]["chapters"])
    chapter_files = sorted(
        chapters_dir.glob(f"{book}-*-web.mp3"),
        key=lambda p: int(p.stem.split("-")[-2])
    )
    
    if len(chapter_files) < expected_chapters:
        print(f"Book incomplete: {len(chapter_files)}/{expected_chapters} chapters")
        return False
    
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = INTERMEDIATE_DIR / f"{book}-web.mp3"
    
    if output_path.exists():
        print(f"Complete book already exists: {output_path}")
        return True
    
    # Get API key for book title
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(f"Error: {e}")
        return False
    
    title_path = generate_book_title(book, api_key)
    if not title_path:
        print("Failed to generate book title")
        return False
    
    # Build concat list
    concat_list = INTERMEDIATE_DIR / f"{book}-concat.txt"
    with open(concat_list, "w") as f:
        # Book title first
        escaped = str(title_path).replace("'", "'\\''")
        f.write(f"file '{escaped}'\n")
        
        for chapter_file in chapter_files:
            chapter_num = int(chapter_file.stem.split("-")[1])
            
            # Chapter title
            chapter_title = CHAPTER_TITLES_DIR / f"chapter-{chapter_num}.mp3"
            if chapter_title.exists():
                escaped_title = str(chapter_title).replace("'", "'\\''")
                f.write(f"file '{escaped_title}'\n")
            
            # Chapter audio
            escaped_chapter = str(chapter_file).replace("'", "'\\''")
            f.write(f"file '{escaped_chapter}'\n")
    
    print(f"Stitching {len(chapter_files)} chapters into complete book...")
    
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-acodec", "copy",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        concat_list.unlink()
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr[:500]}")
            return False
        
        if output_path.exists() and output_path.stat().st_size > 10000:
            size_mb = output_path.stat().st_size / (1024*1024)
            print(f"✓ Complete book created: {output_path}")
            print(f"  Size: {size_mb:.2f} MB")
            return True
    except Exception as e:
        print(f"Compilation error: {e}")
        return False
    
    return False

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
    print("="*60)
    print("Bulk Genesis Generation - Hey Bible Podcast")
    print("="*60)
    
    try:
        api_key = get_api_key()
        print(f"API key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    progress = load_progress()
    book = "genesis"
    
    # Calculate totals
    total_verses = sum(BIBLE_STRUCTURE[book]["chapters"])
    
    # Determine starting point
    if progress.get("book") == book:
        current_chapter = progress.get("chapter", 1)
        current_verse = progress.get("verse", 1)
        completed = progress.get("completed_count", 0)
    else:
        current_chapter = 1
        current_verse = 1
        completed = 0
    
    # Count existing verses
    existing_verses = 0
    for chap_dir in (BOOKS_DIR / book).glob("*"):
        if chap_dir.is_dir():
            existing_verses += len(list(chap_dir.glob("*.mp3")))
    
    if existing_verses > completed:
        completed = existing_verses
    
    print(f"\nStarting from: {book.title()} {current_chapter}:{current_verse}")
    print(f"Verses completed: {completed}/{total_verses}")
    print(f"Remaining: {total_verses - completed}")
    print(f"Total chapters: {len(BIBLE_STRUCTURE[book]['chapters'])}")
    print()
    
    # Verify we're starting at the right place
    if current_chapter == 2 and current_verse == 20:
        print("Note: Will resume from Genesis 2:20")
        # Check what actually exists
        chap1_files = list((BOOKS_DIR / book / "1").glob("*.mp3"))
        chap2_files = list((BOOKS_DIR / book / "2").glob("*.mp3"))
        print(f"  Chapter 1 files: {len(chap1_files)}")
        print(f"  Chapter 2 files: {len(chap2_files)}")
        
        # Verify chapter 1 is complete
        if len(chap1_files) >= 31:  # Genesis 1 has 31 verses
            print("  Chapter 1 appears complete, will stitch it first")
            if stitch_chapter(book, 1):
                if "completed_chapters" not in progress:
                    progress["completed_chapters"] = []
                if "genesis-1" not in progress["completed_chapters"]:
                    progress["completed_chapters"].append("genesis-1")
        
        # Stitch chapter 2 if complete
        if len(chap2_files) >= 25:  # Genesis 2 has 25 verses
            print("  Chapter 2 appears complete, will stitch it")
            if stitch_chapter(book, 2):
                if "genesis-2" not in progress["completed_chapters"]:
                    progress["completed_chapters"].append("genesis-2")
    
    generated_this_run = 0
    stitched_this_run = []
    
    # Main generation loop
    start_time = time.time()
    last_report_time = start_time
    
    while current_chapter <= len(BIBLE_STRUCTURE[book]["chapters"]):
        verses_in_chapter = get_chapter_verse_count(book, current_chapter)
        
        while current_verse <= verses_in_chapter:
            # Progress reporting
            elapsed = time.time() - last_report_time
            if elapsed >= 300:  # Report every 5 minutes
                print(f"\n--- Progress Update ---")
                print(f"  Currently at: {book.title()} {current_chapter}:{current_verse}")
                print(f"  Generated this run: {generated_this_run}")
                print(f"  Total completed: {completed + generated_this_run}")
                print(f"  Chapters stitched: {len(stitched_this_run)}")
                last_report_time = time.time()
            
            # Check if already exists
            verse_file = BOOKS_DIR / book / str(current_chapter) / f"{book}-{current_chapter}-{current_verse}-{TRANSLATION}.mp3"
            if verse_file.exists():
                current_verse += 1
                continue
            
            # Fetch verse text
            verse_text = get_verse_text(book, current_chapter, current_verse)
            if not verse_text:
                print(f"\nFailed to fetch {book} {current_chapter}:{current_verse}, skipping...")
                current_verse += 1
                continue
            
            print(f"[{completed + generated_this_run + 1}/{total_verses}] Gen {current_chapter}:{current_verse} - {verse_text[:50]}...")
            
            # Generate TTS
            if generate_tts(verse_text, verse_file, api_key):
                generated_this_run += 1
                time.sleep(TTS_DELAY)
            else:
                print(f"  ✗ Failed to generate, will retry...")
                time.sleep(RETRY_DELAY)
                continue  # Don't advance verse, retry
            
            current_verse += 1
        
        # Chapter complete - stitch it
        print(f"\nChapter {current_chapter} complete, stitching...")
        if stitch_chapter(book, current_chapter):
            if "completed_chapters" not in progress:
                progress["completed_chapters"] = []
            chapter_key = f"{book}-{current_chapter}"
            if chapter_key not in progress["completed_chapters"]:
                progress["completed_chapters"].append(chapter_key)
                stitched_this_run.append(current_chapter)
        
        # Commit every 10 chapters
        if current_chapter % 10 == 0:
            print(f"\nCommitting progress after chapter {current_chapter}...")
            git_commit(f"Genesis: Chapters 1-{current_chapter} complete ({generated_this_run} new verses)")
        
        # Move to next chapter
        current_chapter += 1
        current_verse = 1
        
        # Update progress
        progress["book"] = book
        progress["chapter"] = current_chapter
        progress["verse"] = current_verse
        progress["completed_count"] = completed + generated_this_run
        save_progress(progress)
    
    # Final chapter stitching for any remaining
    print(f"\n{'='*60}")
    print("All verses generated! Checking chapter completion...")
    print(f"{'='*60}")
    
    for chap_num in range(1, len(BIBLE_STRUCTURE[book]["chapters"]) + 1):
        chapter_key = f"{book}-{chap_num}"
        existing = progress.get("completed_chapters", [])
        if chapter_key not in existing:
            if stitch_chapter(book, chap_num):
                existing.append(chapter_key)
    
    progress["completed_chapters"] = existing
    save_progress(progress)
    
    # Compile complete book
    print(f"\n{'='*60}")
    print("Compiling complete book...")
    print(f"{'='*60}")
    
    if compile_full_book(book):
        progress["book_complete"] = True
        save_progress(progress)
        
        # Final commit
        git_commit(f"Complete: Book of Genesis ({total_verses} verses, 50 chapters)")
        
        print(f"\n{'='*60}")
        print("✓ GENESIS COMPLETE!")
        print(f"{'='*60}")
        print(f"Total verses: {total_verses}")
        print(f"Chapters: 50")
        print(f"Output: {INTERMEDIATE_DIR / 'genesis-web.mp3'}")
    else:
        print("\n✗ Book compilation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
