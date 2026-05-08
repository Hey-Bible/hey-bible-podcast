#!/usr/bin/env python3
"""Fill specific missing verses in the Bible audio"""

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
from bible_text import get_verse_text

BASE_DIR = Path(__file__).parent.parent
VERSES_DIR = BASE_DIR / "verses"

TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"
MIN_REQUEST_DELAY = 1.5
MAX_RETRIES = 3

def get_api_key():
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

def generate_verse(book, chapter, verse, api_key):
    """Generate a single verse"""
    text = get_verse_text(book, chapter, verse)
    if not text:
        print(f"  ⚠️  No text for {book}-{chapter}-{verse}")
        return False
    
    output_path = VERSES_DIR / book / str(chapter) / f"{book}-{chapter}-{verse}-{TRANSLATION}.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists():
        print(f"  ✓ {book}-{chapter}-{verse} already exists")
        return True
    
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
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            audio_data = response.read()
            if len(audio_data) < 1000:
                print(f"  ⚠️  Response too small for {book}-{chapter}-{verse}")
                return False
            
            with open(output_path, "wb") as f:
                f.write(audio_data)
            print(f"  ✓ Generated {book}-{chapter}-{verse}")
            return True
    except Exception as e:
        print(f"  ✗ Failed {book}-{chapter}-{verse}: {e}")
        return False

def main():
    api_key = get_api_key()
    
    # Gap 1: Exodus 28:22
    gaps = [
        ("exodus", 28, 22),
    ]
    
    # Gap 2: Deuteronomy 11:9 through 11:32
    for v in range(9, 33):
        gaps.append(("deuteronomy", 11, v))
    
    print(f"Filling {len(gaps)} missing verses...")
    print("=" * 50)
    
    success = 0
    failed = 0
    
    for book, chapter, verse in gaps:
        if generate_verse(book, chapter, verse, api_key):
            success += 1
        else:
            failed += 1
        time.sleep(MIN_REQUEST_DELAY)
    
    print("=" * 50)
    print(f"Results: {success} succeeded, {failed} failed")

if __name__ == "__main__":
    main()
