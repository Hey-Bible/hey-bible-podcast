#!/usr/bin/env python3
"""Build Exodus chapters 39 and 40 from verse files"""

import subprocess
import re
from pathlib import Path

def build_chapter(chapter_num):
    verses_dir = Path(f'verses/exodus/{chapter_num}')
    chapters_dir = Path('chapters/exodus')
    output_path = chapters_dir / f'exodus-{chapter_num}-web.mp3'
    
    if output_path.exists():
        print(f'Chapter {chapter_num} already exists')
        return True
    
    verse_files = sorted(
        verses_dir.glob('*.mp3'),
        key=lambda p: int(re.search(rf'exodus-{chapter_num}-(\d+)-web', p.name).group(1))
    )
    
    print(f'Building Exodus {chapter_num}: {len(verse_files)} verses')
    
    concat_list = chapters_dir / f'concat-{chapter_num}.txt'
    with open(concat_list, 'w') as f:
        for vf in verse_files:
            escaped_path = str(vf).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
    
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(concat_list),
        '-acodec', 'copy',
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    concat_list.unlink()
    
    if result.returncode == 0 and output_path.exists():
        print(f'  ✓ Created: {output_path} ({output_path.stat().st_size / (1024*1024):.2f} MB)')
        return True
    else:
        print(f'  ✗ Failed: {result.stderr[:500]}')
        return False

for ch in [39, 40]:
    build_chapter(ch)
