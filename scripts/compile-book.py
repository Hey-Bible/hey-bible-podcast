#!/usr/bin/env python3
"""Compile a complete book by stitching together all chapters"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER
import r2

# Configuration
BASE_DIR = Path(__file__).parent.parent
CHAPTERS_DIR = BASE_DIR / "chapters"
CHAPTER_TITLES_DIR = BASE_DIR / "assets" / "titles"
INTERMEDIATE_DIR = BASE_DIR / "intermediate"
STATE_FILE = BASE_DIR / "state" / "progress.json"

def load_progress():
    """Load current progress from state file"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"book": "genesis", "chapter": 1, "verse": 1}

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

def generate_book_title_tts(book_name: str, output_path: Path, api_key: str) -> bool:
    """Generate book title audio using Venice TTS"""
    url = "https://api.venice.ai/api/v1/audio/speech"
    
    # Format: "The Book of Genesis"
    book_display = book_name.replace("-", " ").title()
    text = f"The Book of {book_display}"
    
    payload = {
        "model": "tts-elevenlabs-turbo-v2-5",
        "voice": "Bill",
        "input": text,
        "response_format": "mp3"
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        import urllib.request
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
            
    except Exception as e:
        print(f"  Error generating title: {e}")
        return False

def get_chapter_count(book: str) -> int:
    """Get total chapters in a book"""
    return len(BIBLE_STRUCTURE[book]["chapters"])

def parse_chapter_number(filename: str, book: str) -> int | None:
    """Extract the chapter number from a per-book chapter mp3 filename.

    Accepts both the new convention (`{book}-{N}-web.mp3`, written by
    generate-verses.py) and the legacy `chapter-{N}.mp3` form so existing files
    on the cron machine keep working without a rename.
    """
    name = filename.removesuffix(".mp3")
    if name.startswith(f"{book}-") and name.endswith("-web"):
        middle = name[len(book) + 1 : -len("-web")]
        if middle.isdigit():
            return int(middle)
    if name.startswith("chapter-"):
        rest = name[len("chapter-"):]
        if rest.isdigit():
            return int(rest)
    return None


def check_book_complete(book: str) -> bool:
    """Check if all chapters in a book have been generated"""
    return len(get_existing_chapters(book)) >= get_chapter_count(book)


def get_existing_chapters(book: str) -> list:
    """Get list of existing chapter files sorted by number"""
    book_chapters_dir = CHAPTERS_DIR / book
    if not book_chapters_dir.exists():
        return []

    chapters = []
    for f in book_chapters_dir.glob("*.mp3"):
        n = parse_chapter_number(f.name, book)
        if n is not None:
            chapters.append((n, f))

    return sorted(chapters)

def get_audio_duration(file_path: Path) -> float:
    """Get audio file duration in seconds using ffprobe"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        print(f"  Warning: Could not get duration for {file_path}: {e}")
    
    return 0.0

def compile_book(book: str) -> bool:
    """Compile all chapters into a complete book audio file"""
    print(f"\nCompiling book: {book.title()}")
    print("=" * 60)
    
    # Check if book is complete
    if not check_book_complete(book):
        expected = get_chapter_count(book)
        existing = get_existing_chapters(book)
        print(f"  Book incomplete: {len(existing)}/{expected} chapters")
        return False
    
    chapters = get_existing_chapters(book)
    expected = get_chapter_count(book)
    
    if len(chapters) < expected:
        print(f"  Book incomplete: {len(chapters)}/{expected} chapters")
        return False
    
    print(f"  Found {len(chapters)} chapters")
    
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = INTERMEDIATE_DIR / f"{book}-web.mp3"
    chapters_json_path = INTERMEDIATE_DIR / f"{book}-web.json"
    
    if output_path.exists() and chapters_json_path.exists():
        print(f"  Book already compiled: {output_path}")
        return True
    
    # Generate book title
    print(f"  Generating book title audio...")
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(f"  Error: {e}")
        return False
    
    title_path = INTERMEDIATE_DIR / f"{book}-title.mp3"
    if not title_path.exists():
        if not generate_book_title_tts(book, title_path, api_key):
            print("  Failed to generate book title")
            return False
        print(f"  ✓ Generated book title")
    else:
        print(f"  Book title already exists")
    
    # Build concat list for ffmpeg
    concat_list_path = INTERMEDIATE_DIR / f"{book}-concat.txt"
    
    with open(concat_list_path, "w") as f:
        # Book title first
        escaped_title = str(title_path).replace("'", "'\\''")
        f.write(f"file '{escaped_title}'\n")
        
        # Then each chapter with its title
        for chapter_num, chapter_file in chapters:
            # Chapter number title (e.g., "Chapter 1")
            chapter_title_file = CHAPTER_TITLES_DIR / f"chapter-{chapter_num}.mp3"
            
            if not chapter_title_file.exists():
                print(f"  Warning: Chapter title file missing: {chapter_title_file}")
                continue
            
            escaped_chapter = str(chapter_file).replace("'", "'\\''")
            escaped_chapter_title = str(chapter_title_file).replace("'", "'\\''")
            
            f.write(f"file '{escaped_chapter_title}'\n")
            f.write(f"file '{escaped_chapter}'\n")
    
    print(f"  Stitching {len(chapters)} chapters with titles...")
    
    # Use ffmpeg to concatenate
    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list_path),
            "-acodec", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for full book
        )
        
        # Clean up concat list
        concat_list_path.unlink(missing_ok=True)
        
        if result.returncode != 0:
            print(f"  FFmpeg error: {result.stderr[:500]}")
            return False
        
        # Verify output
        if output_path.exists() and output_path.stat().st_size > 10000:
            print(f"  ✓ Created: {output_path}")
            print(f"  Size: {output_path.stat().st_size / (1024*1024):.2f} MB")
            
            # Build chapter timestamp data
            print(f"  Building chapter timestamp data...")
            chapter_data = []
            current_offset = 0.0
            
            # Track book title duration first
            book_title_duration = get_audio_duration(title_path)
            current_offset += book_title_duration
            
            for chapter_num, chapter_file in chapters:
                # Chapter number title (e.g., "Chapter 1")
                chapter_title_file = CHAPTER_TITLES_DIR / f"chapter-{chapter_num}.mp3"
                
                if not chapter_title_file.exists():
                    print(f"  Warning: Chapter title file missing: {chapter_title_file}")
                    continue
                
                # One entry per chapter spanning both the spoken title clip and
                # the content — podcast clients (Apple, Overcast) render the
                # sidecar as a chapter list, so two entries with the same title
                # would surface as duplicate rows to listeners.
                title_duration = get_audio_duration(chapter_title_file)
                chapter_duration = get_audio_duration(chapter_file)
                chapter_start = current_offset
                current_offset += title_duration + chapter_duration
                chapter_data.append({
                    "number": chapter_num,
                    "title": f"Chapter {chapter_num}",
                    "start": chapter_start,
                    "end": current_offset,
                    "duration": title_duration + chapter_duration,
                })
            
            # Write chapters JSON
            total_duration = get_audio_duration(output_path)

            chapters_data = {
                "book": book,
                "title": book.replace("-", " ").title(),
                "duration": total_duration,
                "chapters": chapter_data
            }
            
            with open(chapters_json_path, "w") as f:
                json.dump(chapters_data, f, indent=2)
            
            print(f"  ✓ Created: {chapters_json_path}")
            print(f"  Total duration: {total_duration:.2f}s ({total_duration/60:.2f} min)")
            print(f"  Tracked {len(chapter_data)} segments")
            
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

def git_commit_intermediate(book: str) -> bool:
    """Commit intermediate book release"""
    try:
        os.chdir(BASE_DIR)
        
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode != 0:
            commit_msg = f"Intermediate release: {book.title()}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "push", "origin", "master"],
                check=True,
                capture_output=True
            )

            print(f"  Committed and pushed: {commit_msg}")
            return True
            
    except Exception as e:
        print(f"  Git error: {e}")
        return False
    
    return False

def find_next_book_to_compile(progress):
    """Find the first complete book that hasn't been compiled/released yet"""
    released = progress.get("released_books", [])
    for book in BOOK_ORDER:
        # Skip already released books
        if book in released:
            continue
        
        # Check if book is complete (all chapters generated)
        if not check_book_complete(book):
            continue
        
        # Check if already compiled
        output_path = INTERMEDIATE_DIR / f"{book}-web.mp3"
        json_path = INTERMEDIATE_DIR / f"{book}-web.json"
        if output_path.exists() and json_path.exists():
            continue
        
        # This book is complete but not compiled
        return book
    
    return None

def main():
    """Main compilation loop"""
    print("=" * 60)
    print("WEB Bible Book Compiler")
    print("=" * 60)
    print()
    
    progress = load_progress()
    current_book = progress["book"]
    
    print(f"Current verse generation: {current_book.title()}")
    print()
    
    # Find the next book that needs compiling
    book_to_compile = find_next_book_to_compile(progress)
    
    if book_to_compile is None:
        print("No books ready for compilation.")
        print("All complete books have been compiled or none are complete yet.")
        return
    
    print(f"Next book to compile: {book_to_compile.title()}")
    print()
    
    # Compile the book
    if not compile_book(book_to_compile):
        print(f"\n✗ Failed to compile book '{book_to_compile}'")
        sys.exit(1)

    print()
    print("Uploading to R2 for review...")
    mp3_file = INTERMEDIATE_DIR / f"{book_to_compile}-web.mp3"
    json_file = INTERMEDIATE_DIR / f"{book_to_compile}-web.json"
    if not r2.upload(mp3_file, json_file):
        print(f"\n✗ Failed to upload book '{book_to_compile}' to R2")
        sys.exit(1)

    print()
    print("Committing intermediate release...")
    git_commit_intermediate(book_to_compile)
    print()
    print(f"✓ Book '{book_to_compile.title()}' ready for release on the 1st!")
    r2.print_review_links(book_to_compile, include_site=False)

if __name__ == "__main__":
    main()
