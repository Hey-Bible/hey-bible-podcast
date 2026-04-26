#!/usr/bin/env python3
"""Generate pre-recorded chapter title clips (Chapter 1 through Chapter 150)"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Configuration
BASE_DIR = Path(__file__).parent.parent
CHAPTER_TITLES_DIR = BASE_DIR / "chapter-titles"

# TTS Configuration
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
            
    except Exception as e:
        print(f"  Error: {e}")
        return False

def number_to_words(n: int) -> str:
    """Convert number to words for TTS"""
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", 
             "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    if n < 10:
        return ones[n]
    elif n < 20:
        return teens[n - 10]
    elif n < 100:
        if n % 10 == 0:
            return tens[n // 10]
        else:
            return tens[n // 10] + " " + ones[n % 10]
    elif n == 100:
        return "one hundred"
    elif n < 110:
        return "one hundred " + ones[n - 100]
    elif n < 120:
        return "one hundred " + teens[n - 110]
    elif n <= 150:
        if n % 10 == 0:
            return "one hundred " + tens[(n - 100) // 10]
        else:
            return "one hundred " + tens[(n - 100) // 10] + " " + ones[n % 10]
    else:
        return str(n)

def main():
    """Generate chapter title clips 1-150"""
    print("=" * 60)
    print("Chapter Title Generator")
    print("Generating 'Chapter N' clips for 1-150")
    print("=" * 60)
    print()
    
    try:
        api_key = get_api_key()
        print(f"API key loaded: {api_key[:10]}...")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    CHAPTER_TITLES_DIR.mkdir(parents=True, exist_ok=True)
    
    generated = []
    failed = []
    
    for n in range(1, 151):
        filename = f"chapter-{n}.mp3"
        output_path = CHAPTER_TITLES_DIR / filename
        
        # Skip if already exists
        if output_path.exists():
            print(f"[{n}/150] Already exists: {filename}")
            generated.append(output_path)
            continue
        
        # Use natural speech pattern
        text = f"Chapter {number_to_words(n)}"
        
        print(f"[{n}/150] Generating: '{text}'")
        
        if generate_tts(text, output_path, api_key):
            print(f"  ✓ Saved: {filename}")
            generated.append(output_path)
            time.sleep(0.3)  # Brief pause
        else:
            print(f"  ✗ Failed: {filename}")
            failed.append(n)
    
    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Generated: {len(generated)} clips")
    print(f"  Failed: {len(failed)} clips")
    if failed:
        print(f"  Failed numbers: {failed}")
    print(f"  Output directory: {CHAPTER_TITLES_DIR}")

if __name__ == "__main__":
    main()
