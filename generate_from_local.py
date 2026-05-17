#!/usr/bin/env python3
"""Generate TTS verses using local JSON data (not bible-api.com)"""

import json
import os
import subprocess
import time
from datetime import datetime

VENICE_API_KEY = os.environ.get("VENICE_API_KEY", "")
BASE_DIR = "/root/.openclaw/workspace-claudius/hey-bible-podcast"
BIBLE_DATA = f"{BASE_DIR}/scripts/data/web-bible.json"
STATE_FILE = f"{BASE_DIR}/state/progress.json"

def load_bible():
    with open(BIBLE_DATA, 'r') as f:
        return json.load(f)

def load_progress():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def save_progress(data):
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_tts(text, output_path):
    """Generate TTS using Venice AI"""
    api_key = VENICE_API_KEY

    payload = json.dumps({
        "model": "tts-elevenlabs-turbo-v2-5",
        "voice": "Bill",
        "input": text
    })

    curl_cmd = [
        'curl', '-s', '-X', 'POST',
        'https://api.venice.ai/v1/audio/speech',
        '-H', f'Authorization: Bearer {api_key}',
        '-H', 'Content-Type: application/json',
        '-d', payload,
        '-o', output_path
    ]

    for attempt in range(3):
        result = subprocess.run(curl_cmd, capture_output=True, timeout=120)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        time.sleep(2)
    return False

def main():
    bible = load_bible()
    progress = load_progress()

    # Get starting position from progress
    start_book = progress.get('book', 'joshua')
    start_chapter = int(progress.get('chapter', 15))
    start_verse = int(progress.get('verse', 14))

    # Books in order
    books = ['joshua', 'judges', 'ruth', '1_samuel', '2_samuel', '1_kings', '2_kings',
             '1_chronicles', '2_chronicles', 'ezra', 'nehemiah', 'esther', 'job', 'psalms',
             'proverbs', 'ecclesiastes', 'song_of_solomon', 'isaiah', 'jeremiah',
             'lamentations', 'ezekiel', 'daniel', 'hosea', 'joel', 'amos', 'obadiah',
             'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah', 'haggai', 'zechariah',
             'malachi', 'matthew', 'mark', 'luke', 'john', 'acts', 'romans', '1_corinthians',
             '2_corinthians', 'galatians', 'ephesians', 'philippians', 'colossians',
             '1_thessalonians', '2_thessalonians', '1_timothy', '2_timothy', 'titus',
             'philemon', 'hebrews', 'james', '1_peter', '2_peter', '1_john', '2_john',
             '3_john', 'jude', 'revelation']

    # Find starting book index
    try:
        start_idx = books.index(start_book)
    except ValueError:
        start_idx = 0

    target_count = 200
    generated = 0
    completed_chapters = set(progress.get('completed_chapters', []))

    for book in books[start_idx:]:
        if book not in bible:
            continue

        chapters = bible[book]
        chapter_nums = sorted([int(c) for c in chapters.keys()])

        for ch_num in chapter_nums:
            # Skip chapters before starting position
            if book == start_book and ch_num < start_chapter:
                continue

            verses = chapters[str(ch_num)]
            verse_nums = sorted([int(v) for v in verses.keys()])

            # Create directory
            ch_dir = f"{BASE_DIR}/books/{book}/{ch_num}"
            os.makedirs(ch_dir, exist_ok=True)

            all_verses_generated = True

            for v_num in verse_nums:
                # Skip verses before starting position
                if book == start_book and ch_num == start_chapter and v_num < start_verse:
                    continue

                if generated >= target_count:
                    break

                text = verses[str(v_num)]
                output_file = f"{ch_dir}/{book}-{ch_num}-{v_num}-web.mp3"

                # Skip if already exists and valid
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    generated += 1
                    continue

                print(f"Generating {book} {ch_num}:{v_num}")

                if generate_tts(text, output_file):
                    generated += 1
                    print(f"  ✓ Generated ({generated}/{target_count})")
                else:
                    print(f"  ✗ Failed")
                    all_verses_generated = False

                # Small delay to respect rate limits
                time.sleep(0.5)

            if generated >= target_count:
                break

            # Mark chapter complete if all verses generated
            if all_verses_generated and book == start_book and ch_num == start_chapter:
                chapter_key = f"{book}-{ch_num}"
                completed_chapters.add(chapter_key)

        if generated >= target_count:
            break

        # Update progress to next book
        if generated >= target_count and book == start_book:
            progress['book'] = books[books.index(book) + 1] if book != books[-1] else book
            progress['chapter'] = 1
            progress['verse'] = 1

    # Update final position
    progress['completed_count'] = progress.get('completed_count', 0) + generated
    progress['completed_chapters'] = sorted(list(completed_chapters))
    progress['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_progress(progress)

    print(f"\n=== Complete ===")
    print(f"Generated: {generated} verses")
    print(f"Total: {progress['completed_count']} / 31,417")
    print(f"Progress: {progress['completed_count']/31417*100:.2f}%")

if __name__ == '__main__':
    main()
