#!/usr/bin/env python3
"""Release compiled book to production with RSS feed update"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from bible_data import BIBLE_STRUCTURE, BOOK_ORDER

# Configuration
BASE_DIR = Path(__file__).parent.parent
INTERMEDIATE_DIR = BASE_DIR / "intermediate"
RELEASES_DIR = BASE_DIR / "releases"
STATE_FILE = BASE_DIR / "state" / "progress.json"
RSS_FILE = BASE_DIR / "podcast.xml"

def load_progress():
    """Load current progress from state file"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"book": "genesis", "chapter": 1, "verse": 1, "released_books": []}

def save_progress(progress):
    """Save progress to state file"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def get_book_title(book: str) -> str:
    """Get display title for a book"""
    return book.replace("-", " ").title()

def get_next_book(book: str) -> str:
    """Get the next book in canonical order"""
    try:
        idx = BOOK_ORDER.index(book)
        if idx < len(BOOK_ORDER) - 1:
            return BOOK_ORDER[idx + 1]
    except ValueError:
        pass
    return None

def ensure_rss_feed_exists():
    """Create initial RSS feed if it doesn't exist"""
    if RSS_FILE.exists():
        return
    
    rss = ET.Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "WEB Bible Audio"
    ET.SubElement(channel, "link").text = "https://claudius.blog"
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "description").text = "Complete World English Bible in audio format"
    
    itunes_author = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author")
    itunes_author.text = "WEB Bible Audio Project"
    
    itunes_category = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}category")
    itunes_category.set("text", "Religion & Spirituality")
    
    itunes_explicit = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit")
    itunes_explicit.text = "no"
    
    tree = ET.ElementTree(rss)
    tree.write(RSS_FILE, encoding="UTF-8", xml_declaration=True)

def get_audio_duration(file_path: Path) -> int:
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
            return int(float(result.stdout.strip()))
    except:
        pass
    
    return 0

def format_duration(seconds: int) -> str:
    """Format seconds as HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def add_rss_item(book: str, release_file: Path) -> bool:
    """Add new book as RSS item"""
    try:
        tree = ET.parse(RSS_FILE)
        root = tree.getroot()
        
        # Find channel
        channel = root.find("channel")
        if channel is None:
            print("  Error: No channel found in RSS")
            return False
        
        # Check if this book is already in the feed
        book_title = get_book_title(book)
        for item in channel.findall("item"):
            title_elem = item.find("title")
            if title_elem is not None and title_elem.text == book_title:
                print(f"  Book already in RSS feed")
                return True
        
        # Get file info
        file_size = release_file.stat().st_size
        duration = get_audio_duration(release_file)
        
        # Create new item
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "title").text = book_title
        ET.SubElement(item, "link").text = f"https://claudius.blog/bible/{book}"
        ET.SubElement(item, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        ET.SubElement(item, "description").text = f"The Book of {book_title} from the World English Bible"
        
        # iTunes elements
        itunes_duration = ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration")
        itunes_duration.text = format_duration(duration)
        
        itunes_explicit = ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit")
        itunes_explicit.text = "no"
        
        # Enclosure
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", f"https://claudius.blog/bible/releases/{book}-complete.mp3")
        enclosure.set("length", str(file_size))
        enclosure.set("type", "audio/mpeg")
        
        # Guid
        guid = ET.SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"web-bible-{book}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Write updated RSS
        tree.write(RSS_FILE, encoding="UTF-8", xml_declaration=True)
        
        print(f"  ✓ Added RSS entry for {book_title}")
        print(f"  Duration: {format_duration(duration)}")
        print(f"  Size: {file_size / (1024*1024):.2f} MB")
        return True
        
    except Exception as e:
        print(f"  Error updating RSS: {e}")
        return False

def release_book(book: str) -> bool:
    """Copy intermediate book to releases and update RSS"""
    print(f"\nReleasing book: {book.title()}")
    print("=" * 60)
    
    intermediate_file = INTERMEDIATE_DIR / f"{book}-complete.mp3"
    
    if not intermediate_file.exists():
        print(f"  Error: Intermediate file not found: {intermediate_file}")
        print(f"  Run compile-book.py first on the 25th!")
        return False
    
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    release_file = RELEASES_DIR / f"{book}-complete.mp3"
    
    if release_file.exists():
        print(f"  Release already exists: {release_file}")
    else:
        print(f"  Copying to releases...")
        shutil.copy2(intermediate_file, release_file)
        print(f"  ✓ Released: {release_file}")
    
    # Update RSS feed
    print(f"  Updating RSS feed...")
    ensure_rss_feed_exists()
    
    if not add_rss_item(book, release_file):
        print(f"  Warning: Failed to add RSS item")
    
    return True

def git_commit_release(book: str) -> bool:
    """Commit and push release"""
    try:
        os.chdir(BASE_DIR)
        
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        
        if result.returncode != 0:
            commit_msg = f"Release: {get_book_title(book)}"
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
            
            print(f"  Committed and pushed: {commit_msg}")
            return True
            
    except Exception as e:
        print(f"  Git error: {e}")
        return False
    
    return False

def advance_to_next_book(progress, current_book: str):
    """Advance progress to next book"""
    next_book = get_next_book(current_book)
    
    if next_book:
        progress["book"] = next_book
        progress["chapter"] = 1
        progress["verse"] = 1
        
        # Mark current book as released
        if "released_books" not in progress:
            progress["released_books"] = []
        progress["released_books"].append(current_book)
        
        save_progress(progress)
        print(f"\n✓ Advanced to next book: {next_book.title()}")
    else:
        print(f"\n🎉 END OF BIBLE REACHED!")
        progress["completed"] = True
        save_progress(progress)

def main():
    """Main release loop"""
    print("=" * 60)
    print("WEB Bible Book Release")
    print("=" * 60)
    print()
    
    progress = load_progress()
    current_book = progress["book"]
    released_books = progress.get("released_books", [])
    
    print(f"Current book: {current_book.title()}")
    print(f"Previously released: {len(released_books)} books")
    if released_books:
        print(f"  {', '.join(b.title() for b in released_books)}")
    print()
    
    # Check if current book has intermediate file
    intermediate_file = INTERMEDIATE_DIR / f"{current_book}-complete.mp3"
    
    if not intermediate_file.exists():
        print(f"No intermediate file found for {current_book.title()}")
        print(f"The book may not be complete yet, or compile-book.py hasn't run.")
        return
    
    # Check if already released
    release_file = RELEASES_DIR / f"{current_book}-complete.mp3"
    if release_file.exists() and current_book in released_books:
        print(f"Book '{current_book.title()}' is already released.")
        return
    
    # Release the book
    if release_book(current_book):
        print()
        print("Committing release...")
        git_commit_release(current_book)
        
        print()
        print("Advancing to next book...")
        advance_to_next_book(progress, current_book)
        
        print()
        print("=" * 60)
        print(f"✓ SUCCESSFULLY RELEASED: {get_book_title(current_book)}")
        print("=" * 60)
    else:
        print(f"\n✗ Failed to release book '{current_book}'")
        sys.exit(1)

if __name__ == "__main__":
    main()
