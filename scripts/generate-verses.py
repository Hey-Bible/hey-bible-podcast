#!/usr/bin/env python3
"""Generate WEB Bible audio verses using Venice TTS (ElevenLabs Bill voice)"""

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
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER, get_next_book_chapter_verse
from bible_text import get_verse_text

# Configuration
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
BOOKS_DIR = BASE_DIR / "verses"
CHAPTERS_DIR = BASE_DIR / "chapters"
STATE_FILE = STATE_DIR / "progress.json"

# TTS Configuration
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"
DAILY_BATCH_SIZE = 500  # verses per day

# Rate limiting: Venice Audio API = 120 requests/minute = 2/sec
# Use 1.5s min delay to stay well under limit (40 req/min)
MIN_REQUEST_DELAY = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds

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

def generate_tts(text: str, output_path: Path, api_key: str, retry_count: int = 0) -> bool:
    """Generate TTS using Venice API with rate limit handling"""
    url = "https://api.venice.ai/api/v1/audio/speech"
    
    # Normalize smart quotes to straight quotes before TTS
    text = (text
        .replace("\u201c", '"')   # left double quotation mark
        .replace("\u201d", '"')   # right double quotation mark
        .replace("\u2018", "'")    # left single quotation mark
        .replace("\u2019", "'"))  # right single quotation mark
    
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
            
            # Check rate limit headers
            remaining = response.headers.get('x-ratelimit-remaining-requests')
            if remaining and int(remaining) < 10:
                print(f"  Rate limit warning: {remaining} requests remaining")
            
            if len(audio_data) < 1000:
                print(f"  Warning: Response too small ({len(audio_data)} bytes)")
                return False
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            return True
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:200]
        if e.code == 429:
            if retry_count < MAX_RETRIES:
                wait = RETRY_BACKOFF * (2 ** retry_count)
                print(f"  Rate limited (429), waiting {wait}s before retry...")
                time.sleep(wait)
                return generate_tts(text, output_path, api_key, retry_count + 1)
            else:
                print(f"  Rate limited (429), max retries exceeded")
        print(f"  HTTP Error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def load_progress():
    """Load current progress from state file"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    
    return {
        "book": "genesis",
        "chapter": 1,
        "verse": 1,
        "completed_count": 0,
        "last_run": None,
        "completed_chapters": []
    }

def save_progress(progress):
    """Save progress to state file"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_chapter_verse_count(book: str, chapter: int) -> int:
    """Get total verses in a chapter"""
    return BIBLE_STRUCTURE[book]["chapters"][chapter - 1]

def check_chapter_complete(book: str, chapter: int) -> bool:
    """Check if all verses in a chapter have been generated"""
    chapter_dir = BOOKS_DIR / book / str(chapter)
    if not chapter_dir.exists():
        return False
    
    expected_verses = get_chapter_verse_count(book, chapter)
    existing_files = list(chapter_dir.glob("*.mp3"))
    
    return len(existing_files) >= expected_verses

def stitch_chapter(book: str, chapter: int) -> bool:
    """Stitch all verses in a chapter into a single MP3 file"""
    chapter_dir = BOOKS_DIR / book / str(chapter)
    output_dir = CHAPTERS_DIR / book
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{book}-{chapter}-web.mp3"
    
    if output_path.exists():
        print(f"  Chapter file already exists: {output_path}")
        return True
    
    # Get all verse files sorted by verse number
    verse_files = sorted(
        chapter_dir.glob("*.mp3"),
        key=lambda p: int(p.stem.split("-")[-2])  # Extract verse number from filename
    )
    
    if not verse_files:
        print(f"  No verse files found for {book} {chapter}")
        return False
    
    expected_verses = get_chapter_verse_count(book, chapter)
    if len(verse_files) < expected_verses:
        print(f"  Chapter {chapter} incomplete: {len(verse_files)}/{expected_verses} verses")
        return False
    
    print(f"  Stitching {len(verse_files)} verses into chapter file...")
    
    # Create concat list file for ffmpeg
    concat_list = output_dir / f"concat-{chapter}.txt"
    with open(concat_list, "w") as f:
        for vf in verse_files:
            # Escape single quotes in path for ffmpeg
            escaped_path = str(vf).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    # Use ffmpeg to concatenate
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-acodec", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Clean up concat list
        concat_list.unlink()
        
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr[:500]}")
            return False
        
        print(f"  ✓ Created: {output_path}")
        
        # Verify the output file
        if output_path.exists() and output_path.stat().st_size > 1000:
            # Keep individual verse files for backup/reference
            # (commented out deletion code - we want to preserve verses)
            # for vf in verse_files:
            #     vf.unlink()
            
            print(f"  ✓ Kept {len(verse_files)} individual verse files")
            return True
        else:
            print(f"  Output file too small or missing")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  FFmpeg timed out")
        return False
    except Exception as e:
        print(f"  Error during stitch: {e}")
        return False

def chapter_mp3_path(book: str, chapter: int) -> Path:
    """Canonical per-chapter stitched file path."""
    return CHAPTERS_DIR / book / f"{book}-{chapter}-web.mp3"


def process_completed_chapters(progress):
    """Stitch any complete chapters that are missing a chapter MP3.

    Runs after each daily verse batch. Scope:
    - Current book: all chapters up through the cursor chapter
    - Plus any earlier book that is fully verse-complete but still missing
      chapter files (so we don't strand e.g. Joshua after the cursor moved on)

    Also re-stitches when a chapter is listed in completed_chapters but the
    on-disk chapter MP3 is gone (previously we skipped forever once marked).
    """
    completed = progress.get("completed_chapters", [])
    completed_set = set(completed)
    newly_stitched = []

    def maybe_stitch(book: str, chapter_num: int) -> None:
        chapter_key = f"{book}-{chapter_num}"
        out = chapter_mp3_path(book, chapter_num)
        # Skip only if already on disk
        if out.exists():
            if chapter_key not in completed_set:
                completed.append(chapter_key)
                completed_set.add(chapter_key)
            return
        if not check_chapter_complete(book, chapter_num):
            return
        print(f"\nDetected complete chapter needing stitch: {book.title()} {chapter_num}")
        if stitch_chapter(book, chapter_num):
            if chapter_key not in completed_set:
                completed.append(chapter_key)
                completed_set.add(chapter_key)
            newly_stitched.append(chapter_key)

    # 1) Current book through cursor chapter (normal daily path)
    current_book = progress["book"]
    current_chapter = progress["chapter"]
    if current_book in BIBLE_STRUCTURE:
        for chapter_num in range(1, current_chapter + 1):
            maybe_stitch(current_book, chapter_num)

    # 2) Backfill earlier books: any verse-complete chapter missing its MP3
    #    (cursor may have moved on, leaving e.g. Joshua stranded)
    try:
        current_idx = BOOK_ORDER.index(current_book)
    except ValueError:
        current_idx = len(BOOK_ORDER)
    for book in BOOK_ORDER[:current_idx]:
        chapter_counts = BIBLE_STRUCTURE[book]["chapters"]
        for chapter_num in range(1, len(chapter_counts) + 1):
            maybe_stitch(book, chapter_num)

    if newly_stitched or len(completed) != len(progress.get("completed_chapters", [])):
        progress["completed_chapters"] = completed
        save_progress(progress)
        if newly_stitched:
            print(f"\nNewly stitched chapters: {len(newly_stitched)}")

    return newly_stitched

def git_commit_changes(book: str, chapter: int, count: int, stitched: list):
    """Commit and push generated verses and chapter files.
    
    Now robustly pulls/rebase from origin first (per request), then commits
    new verses, then pushes with retry. This ensures pushes succeed after
    every run even if remote has drifted.
    """
    try:
        os.chdir(BASE_DIR)
        
        # Always pull latest from origin first using rebase (keeps linear history)
        # This incorporates any remote changes (README updates, etc.) before our new work
        print("  Pulling latest from origin (rebase to integrate remote)...")
        pull_result = subprocess.run(
            ["git", "pull", "--rebase", "origin", "master"],
            capture_output=True,
            text=True
        )
        if pull_result.returncode != 0:
            print(f"  Warning: pull --rebase returned {pull_result.returncode}")
            if pull_result.stderr:
                print(f"    {pull_result.stderr.strip()[:250]}")
            # Continue; push may still succeed or will surface the issue
        
        # Add new files (verses + any stitched chapters + progress)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode != 0:
            commit_msg = f"Add {count} verses: {book.title()} {chapter}"
            if stitched:
                commit_msg += f" (+{len(stitched)} chapters stitched)"
            
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True
            )
            
            # Push with simple retry for transient network issues
            print("  Pushing to origin/master...")
            pushed = False
            last_err = None
            for attempt in range(3):
                try:
                    subprocess.run(
                        ["git", "push", "origin", "master"],
                        check=True,
                        capture_output=True
                    )
                    pushed = True
                    break
                except subprocess.CalledProcessError as push_err:
                    last_err = push_err
                    if attempt < 2:
                        print(f"  Push attempt {attempt + 1} failed, retrying in 5s...")
                        time.sleep(5)
                    else:
                        raise
            
            if pushed:
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
    
    # Random startup delay (0-10s) to stagger concurrent runs
    # This prevents thundering herd when multiple instances start together
    import random
    startup_delay = random.uniform(0, 10)
    if startup_delay > 1:
        print(f"Staggering start: waiting {startup_delay:.1f}s...")
        time.sleep(startup_delay)
    
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
    print(f"Previously stitched chapters: {len(progress.get('completed_chapters', []))}")
    print(f"Daily batch size: {DAILY_BATCH_SIZE} verses")
    print()
    
    generated = []
    failed = []
    
    for i in range(DAILY_BATCH_SIZE):
        print(f"[{i+1}/{DAILY_BATCH_SIZE}] {current_book.title()} {current_chapter}:{current_verse}")
        
        verse_text = get_verse_text(current_book, current_chapter, current_verse)
        if not verse_text:
            print(f"  Verse text not found in local WEB JSON, skipping...")
            failed.append((current_book, current_chapter, current_verse))
            
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
            print(f"  Text: {verse_text[:60]}...")
            print(f"  Generating audio...")
            
            if generate_tts(verse_text, output_path, api_key):
                print(f"  ✓ Saved: {output_path}")
                generated.append(output_path)
                # Rate limiting: stay well under 120 req/min (2/sec)
                # Add jitter to prevent thundering herd with concurrent runs
                import random
                sleep_time = MIN_REQUEST_DELAY + random.uniform(0, 0.5)
                time.sleep(sleep_time)
            else:
                print(f"  ✗ Failed to generate")
                failed.append((current_book, current_chapter, current_verse))
                # Still delay on failure to avoid hammering
                time.sleep(1.0)
        
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
    print(f"Generation Summary:")
    print(f"  Generated: {len(generated)} verses")
    print(f"  Failed: {len(failed)} verses")
    print(f"  Total completed: {progress['completed_count']} verses")
    print(f"  Next verse: {current_book.title()} {current_chapter}:{current_verse}")
    
    # Process completed chapters
    print()
    print("Checking for completed chapters...")
    stitched = process_completed_chapters(progress)
    
    # Git commit if we generated anything
    if generated or stitched:
        print()
        print("Committing changes...")
        git_commit_changes(current_book, current_chapter, len(generated), stitched)
    
    print()
    print(f"Progress saved to: {STATE_FILE}")

if __name__ == "__main__":
    main()
