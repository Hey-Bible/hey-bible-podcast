#!/usr/bin/env python3
"""Generate missing WEB Bible audio verses for Leviticus chapters 13, 14, 25, 26, 27"""

import json
import os
import time
import sys
from pathlib import Path

import urllib.request
import urllib.error

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from bible_text import get_verse_text

# Configuration
BASE_DIR = Path(__file__).parent.parent
VERSE_DIR = BASE_DIR / "verses" / "leviticus"

# TTS Configuration
TTS_VOICE = "Bill"
TTS_MODEL = "tts-elevenlabs-turbo-v2-5"
TRANSLATION = "web"

VENICE_API_KEY = "VENICE-INFERENCE-KEY-WGD74Sc663fbvu59-em7RzqgHkB90tx06_kLqT91c9"

# Missing verses by chapter
MISSING_VERSES = {
    13: list(range(55, 60)),      # verses 55-59 (5 verses)
    14: list(range(1, 46)),        # verses 1-45 (45 verses)
    25: list(range(16, 56)),       # verses 16-55 (40 verses)
    26: list(range(1, 47)),        # verses 1-46 (46 verses)
    27: list(range(1, 35)),        # verses 1-34 (34 verses)
}

def generate_tts(text: str, output_path: Path) -> bool:
    """Generate TTS using Venice API"""
    url = "https://api.venice.ai/api/v1/audio/speech"

    payload = {
        "model": TTS_MODEL,
        "voice": TTS_VOICE,
        "input": text,
        "response_format": "mp3"
    }

    headers = {
        "Authorization": f"Bearer {VENICE_API_KEY}",
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

def main():
    print("=" * 60)
    print("Generating Missing Leviticus Verses")
    print("=" * 60)
    print()

    generated = []
    failed = []

    for chapter, verses in sorted(MISSING_VERSES.items()):
        print(f"\nChapter {chapter}: {len(verses)} verses to generate")
        print("-" * 40)

        for verse in verses:
            verse_text = get_verse_text("leviticus", chapter, verse)

            if not verse_text:
                print(f"  Leviticus {chapter}:{verse} - TEXT NOT FOUND, skipping")
                failed.append((chapter, verse))
                continue

            output_path = VERSE_DIR / str(chapter) / f"leviticus-{chapter}-{verse}-{TRANSLATION}.mp3"

            # Skip if already exists
            if output_path.exists():
                print(f"  Leviticus {chapter}:{verse} - already exists, skipping")
                generated.append(output_path)
                continue

            print(f"  Leviticus {chapter}:{verse} - generating...")
            print(f"    Text: {verse_text[:60]}...")

            if generate_tts(verse_text, output_path):
                print(f"    ✓ Saved: {output_path}")
                generated.append(output_path)
                time.sleep(0.5)  # Rate limiting
            else:
                print(f"    ✗ Failed")
                failed.append((chapter, verse))

    print()
    print("=" * 60)
    print("Generation Summary:")
    print(f"  Generated: {len(generated)} verses")
    print(f"  Failed: {len(failed)} verses")

    if failed:
        print("\nFailed verses:")
        for chapter, verse in failed:
            print(f"  - Leviticus {chapter}:{verse}")

if __name__ == "__main__":
    main()
