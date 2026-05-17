#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime

VENICE_API_KEY = "VENICE-INFERENCE-KEY-WGD74Sc663fbvu59-em7RzqgHkB90tx06_kLqT91c9"
BASE_DIR = "/root/.openclaw/workspace-claudius/hey-bible-podcast"
STATE_FILE = f"{BASE_DIR}/state/progress.json"

TARGET_COUNT = 200

def load_progress():
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def save_progress(data):
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def curl_with_retry(url, max_retries=5, timeout=30):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', str(timeout), url],
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            if result.returncode == 0 and result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return None
            else:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
    return None

def get_verse_text(book, chapter, verse):
    url = f"https://bible-api.com/{book}+{chapter}:{verse}?translation=web"
    data = curl_with_retry(url)
    if data:
        text = data.get('text', '')
        text = ' '.join(text.split())
        return text.strip()
    return None

def get_chapter_verse_count(book, chapter):
    url = f"https://bible-api.com/{book}+{chapter}"
    data = curl_with_retry(url)
    if data:
        return len(data.get('verses', []))
    return 0

def generate_tts(text, output_file):
    """Generate TTS using Venice AI"""
    payload = json.dumps({
        "model": "tts-kokoro",
        "voice": "af_sky",
        "input": text
    })

    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST',
             'https://api.venice.ai/api/v1/audio/speech',
             '-H', f'Authorization: Bearer {VENICE_API_KEY}',
             '-H', 'Content-Type: application/json',
             '-d', payload,
             '--output', output_file],
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 1000
    except Exception as e:
        print(f"TTS error: {e}")
        return False

def main():
    progress = load_progress()
    current_book = progress.get('book', 'joshua')
    current_chapter = progress.get('chapter', 24)
    current_verse = progress.get('verse', 8)
    completed_count = progress.get('completed_count', 6296)
    completed_chapters = progress.get('completed_chapters', [])

    # Start from next verse
    current_verse += 1

    print(f"Starting TTS generation from {current_book} {current_chapter}:{current_verse}")
    print(f"Target: {TARGET_COUNT} verses")
    print(f"Current completed: {completed_count}")

    generated = 0
    consecutive_errors = 0

    while generated < TARGET_COUNT:
        verse_text = get_verse_text(current_book, current_chapter, current_verse)

        if not verse_text:
            consecutive_errors += 1
            if consecutive_errors >= 5:
                print(f"Too many consecutive errors. Stopping at {current_book} {current_chapter}:{current_verse}")
                break
            print(f"Error fetching verse, retrying... ({consecutive_errors}/5)")
            time.sleep(3)
            continue

        consecutive_errors = 0

        output_dir = f"{BASE_DIR}/books/{current_book}/{current_chapter}"
        os.makedirs(output_dir, exist_ok=True)

        output_file = f"{output_dir}/{current_book}-{current_chapter}-{current_verse}-web.mp3"

        # Check if file exists and has valid size
        existing_file_size = 0
        if os.path.exists(output_file):
            existing_file_size = os.path.getsize(output_file)

        if existing_file_size > 1000:  # Valid file
            print(f"[{generated+1}/{TARGET_COUNT}] Skipping existing: {current_book} {current_chapter}:{current_verse}")
        else:
            if existing_file_size > 0:
                os.remove(output_file)  # Remove invalid file

            print(f"[{generated+1}/{TARGET_COUNT}] Generating: {current_book} {current_chapter}:{current_verse}")
            print(f"  Text: {verse_text[:80]}...")

            if generate_tts(verse_text, output_file):
                file_size = os.path.getsize(output_file)
                print(f"  ✓ Saved: {output_file} ({file_size} bytes)")
            else:
                print(f"  ✗ Failed to generate TTS")
                time.sleep(1)
                continue

            time.sleep(0.5)

        generated += 1
        completed_count += 1

        progress['book'] = current_book
        progress['chapter'] = current_chapter
        progress['verse'] = current_verse
        progress['completed_count'] = completed_count
        progress['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        chapter_key = f"{current_book}-{current_chapter}"
        if chapter_key not in completed_chapters:
            completed_chapters.append(chapter_key)
        progress['completed_chapters'] = completed_chapters

        save_progress(progress)

        current_verse += 1

        chapter_verses = get_chapter_verse_count(current_book, current_chapter)
        if current_verse > chapter_verses:
            print(f"Chapter {current_book} {current_chapter} complete ({chapter_verses} verses). Moving to next chapter.")
            current_chapter += 1
            current_verse = 1

            # Only stop after Joshua 24 - that's the end of the book
            if current_book == "joshua" and current_chapter > 24:
                print("Book Joshua complete!")
                # Move to next book (Judges)
                current_book = "judges"
                current_chapter = 1
                current_verse = 1
                print(f"Moving to next book: {current_book} {current_chapter}:{current_verse}")

        if generated % 25 == 0:
            percentage = (completed_count / 31417) * 100
            print(f"\n=== PROGRESS REPORT ===")
            print(f"Verses generated this run: {generated}/{TARGET_COUNT}")
            print(f"Current position: {current_book} {current_chapter}:{current_verse}")
            print(f"Total completed: {completed_count}/31,417 ({percentage:.2f}%)")
            print(f"=======================\n")

    percentage = (completed_count / 31417) * 100
    print(f"\n=== TASK COMPLETE ===")
    print(f"Verses generated this run: {generated}")
    print(f"Final position: {current_book} {current_chapter}:{current_verse}")
    print(f"Total completed: {completed_count}/31,417 ({percentage:.2f}%)")
    print(f"=====================")

if __name__ == "__main__":
    main()
