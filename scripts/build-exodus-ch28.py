#!/usr/bin/env python3
"""Build Exodus chapter 28 from verse files"""

import subprocess
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
VERSES_DIR = BASE_DIR / "verses" / "exodus" / "28"
CHAPTERS_DIR = BASE_DIR / "chapters" / "exodus"

output_path = CHAPTERS_DIR / "exodus-28-web.mp3"

# Get all verse files sorted by verse number
verse_files = sorted(
    VERSES_DIR.glob("*.mp3"),
    key=lambda p: int(re.search(r'exodus-28-(\d+)-web', p.name).group(1))
)

print(f"Found {len(verse_files)} verse files for Exodus 28")

# Create concat list file for ffmpeg
concat_list = CHAPTERS_DIR / "concat-28.txt"
with open(concat_list, "w") as f:
    for vf in verse_files:
        escaped_path = str(vf).replace("'", "'\\''")
        f.write(f"file '{escaped_path}'\n")

print(f"Stitching {len(verse_files)} verses into chapter file...")

# Use ffmpeg to concatenate
cmd = [
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", str(concat_list),
    "-acodec", "copy",
    str(output_path)
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

# Clean up concat list
concat_list.unlink()

if result.returncode != 0:
    print(f"FFmpeg error: {result.stderr[:500]}")
    exit(1)

if output_path.exists() and output_path.stat().st_size > 1000:
    print(f"✓ Created: {output_path}")
    print(f"  Size: {output_path.stat().st_size / (1024*1024):.2f} MB")
else:
    print(f"Output file too small or missing")
    exit(1)
