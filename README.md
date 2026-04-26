# WEB Bible Audio Project

Complete audio Bible using ElevenLabs Bill voice via Venice AI TTS.

## Project Structure

```
web-bible-audio/
├── books/                  # Individual verse audio files (deleted after chapter stitch)
│   └── {book}/
│       └── {chapter}/
│           └── {book}-{chapter}-{verse}-web.mp3
├── chapters/              # Stitched chapter audio files
│   └── {book}/
│       └── chapter-{N}.mp3
├── chapter-titles/        # Pre-generated "Chapter N" audio clips
│   └── chapter-{N}.mp3
├── intermediate/          # Compiled book releases (monthly 25th)
│   └── {book}-complete.mp3
├── releases/              # Final production releases (monthly 1st)
│   └── {book}-complete.mp3
├── scripts/               # Automation scripts
│   ├── generate-verses.py      # Daily: Generate 50 verses + stitch chapters
│   ├── generate-chapter-titles.py  # One-time: Generate Chapter 1-150 clips
│   ├── compile-book.py         # Monthly 25th: Compile complete book
│   ├── release-book.py         # Monthly 1st: Release to production
│   ├── bible_data.py           # Bible structure data
│   └── run-daily.sh            # Legacy cron wrapper
├── state/                 # Progress tracking
│   └── progress.json
└── podcast.xml           # RSS feed for podcast distribution
```

## Stats

- **Total verses:** 31,417
- **Daily batch:** 50 verses
- **Estimated completion:** ~1.7 years
- **Voice:** ElevenLabs Bill (via Venice TTS)
- **Translation:** WEB (World English Bible)

## Cron Schedule

### Daily (7PM EST)
**Script:** `scripts/generate-verses.py`

- Generate 50 verses
- Detect completed chapters (all verses present)
- Stitch completed chapters using ffmpeg
- Delete individual verse files after successful stitch
- Update progress.json

### Monthly 25th
**Script:** `scripts/compile-book.py`

- Check if current book is complete (all chapters present)
- Generate book title audio: "The Book of {BookName}"
- Stitch together: book-title + chapter-1 + chapter-title-1 + chapter-2 + ...
- Save to `intermediate/{book}-complete.mp3`
- Git commit intermediate release

### Monthly 1st
**Script:** `scripts/release-book.py`

- Copy `intermediate/{book}-complete.mp3` to `releases/{book}-complete.mp3`
- Update RSS feed (podcast.xml) with new episode
- Advance to next book in progress.json
- Git commit and push releases

## Manual Commands

### Generate verses (daily task)
```bash
cd ~/.openclaw/workspace-claudius/web-bible-audio
python3 scripts/generate-verses.py
```

### Compile book (monthly 25th)
```bash
cd ~/.openclaw/workspace-claudius/web-bible-audio
python3 scripts/compile-book.py
```

### Release book (monthly 1st)
```bash
cd ~/.openclaw/workspace-claudius/web-bible-audio
python3 scripts/release-book.py
```

### Generate chapter title clips (one-time setup)
```bash
cd ~/.openclaw/workspace-claudius/web-bible-audio
python3 scripts/generate-chapter-titles.py
```

## State Tracking

Progress tracked in `state/progress.json`:
- Current book/chapter/verse
- Completed verse count
- Completed chapters list
- Released books list
- Last run timestamps

## File Naming Convention

**Verse files:** `{book}-{chapter}-{verse}-web.mp3`  
**Chapter files:** `chapter-{N}.mp3`  
**Book releases:** `{book}-complete.mp3`

Example: `genesis-1-1-web.mp3`

## Requirements

- Python 3.8+
- ffmpeg (for audio concatenation)
- Venice API key (configured in openclaw.json)
- Git access for commits

## FFmpeg Concatenation

The project uses ffmpeg's concat demuxer for lossless audio stitching:

```bash
# Chapter stitching (verses -> chapter)
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy chapter-N.mp3

# Book compilation (chapters -> book)
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy book-complete.mp3
```

Individual verse files are deleted after successful chapter stitching to save space.

## Current Progress

See `state/progress.json` for real-time progress.

Last updated: Genesis 2:20, 50 verses completed
