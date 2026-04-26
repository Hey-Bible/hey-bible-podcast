# Hey Bible Podcast

The whole Bible read aloud, one book at a time. Audio generated with the ElevenLabs Bill voice via Venice AI TTS, published as a monthly podcast at [✝.fm](https://xn--pci.fm).

- **Audio pipeline** (Python) — generates verses daily, stitches chapters as they fill in, compiles each book monthly, releases on the 1st as a GitHub Release asset.
- **Web player** (Astro + Tailwind v4 in `web/`) — static site at ✝.fm with per-book pages, chapter seek, and a Podcasting 2.0 RSS feed.

## Project Structure

```
hey-bible-podcast/
├── verses/                 # Individual verse audio files (deleted after chapter stitch)
│   └── {book}/{chapter}/{book}-{chapter}-{verse}-web.mp3
├── chapters/               # Stitched chapter audio files
│   └── {book}/chapter-{N}.mp3
├── chapter-titles/         # Pre-generated "Chapter N" audio clips (1–150)
├── intermediate/           # Compiled book + chapter sidecar (monthly 25th, pre-release)
│   ├── {book}-complete.mp3
│   └── {book}-chapters.json
├── releases/               # Final production releases (monthly 1st)
│   └── {book}-complete.mp3
├── scripts/                # Audio pipeline
│   ├── generate-verses.py          # Daily: 50 verses + chapter stitch
│   ├── generate-chapter-titles.py  # One-time: Chapter 1–150 clips
│   ├── compile-book.py             # Monthly 25th: stitch chapters → book + sidecar JSON
│   ├── release-book.py             # Monthly 1st: upload to GitHub Release, patch books.json
│   ├── bible_data.py               # 66-book chapter/verse counts
│   └── run-daily.sh                # Cron wrapper
├── state/
│   └── progress.json       # Current book/chapter/verse, completed chapters
├── web/                    # Astro site for ✝.fm — see web/README.md
└── .github/workflows/
    └── deploy-web.yml      # Build + deploy web/ to GitHub Pages on push
```

## Stats

- **Total verses:** 31,417
- **Daily batch:** 50 verses
- **Estimated completion:** ~1.7 years
- **Voice:** ElevenLabs Bill (via Venice TTS)
- **Translation:** [World English Bible](https://worldenglish.bible) (public domain)

## Cron Schedule

### Daily — `scripts/generate-verses.py`
- Fetch 50 verses from bible-api.com, generate MP3s via Venice TTS
- Detect chapters where every verse is now present, stitch with ffmpeg
- Delete the per-verse files for completed chapters
- Update `state/progress.json`
- Commit and push

### Monthly 25th — `scripts/compile-book.py`
- Verify the current book has all chapters
- Generate the spoken book-title audio ("The Book of Genesis")
- Stitch: book-title + (chapter-title-N + chapter-N) for every chapter, into `intermediate/{book}-complete.mp3`
- Emit `intermediate/{book}-chapters.json` — a chapter sidecar with start/end offsets in seconds
- Commit intermediate output

### Monthly 1st — `scripts/release-book.py`
- Move the compiled MP3 + sidecar JSON to `releases/`
- Create a GitHub Release tagged `{book}-{YYYY-MM}` and upload both as assets
- Patch `web/src/data/books.json`: set the book's `status: "available"`, `releaseTag`, and `releaseSize` (bytes)
- Commit and push — that push triggers `deploy-web.yml`, which rebuilds ✝.fm with the new release

## Chapter sidecar JSON

`{book}-chapters.json` is uploaded as a release asset alongside `{book}-complete.mp3` and is used both by the web chapter player and by the `<podcast:chapters>` link in the RSS feed (Apple Podcasts / Overcast / Pocket Casts render it as the chapter list).

```json
{
  "book": "genesis",
  "title": "Genesis",
  "duration": 12345.67,
  "releaseTag": "genesis-2026-05",
  "chapters": [
    { "number": 1, "title": "Chapter 1", "start": 0,     "end": 240.5,  "duration": 240.5 },
    { "number": 2, "title": "Chapter 2", "start": 240.5, "end": 495.1,  "duration": 254.6 }
  ]
}
```

One entry per chapter — `start` is the offset of the spoken "Chapter N" intro, `end` is where the chapter content finishes.

## Manual Commands

```bash
cd ~/.openclaw/workspace-claudius/hey-bible-podcast

python3 scripts/generate-verses.py          # daily
python3 scripts/compile-book.py             # monthly 25th
python3 scripts/release-book.py             # monthly 1st
python3 scripts/generate-chapter-titles.py  # one-time setup
```

## File naming convention

| Kind             | Pattern                              | Example                  |
|------------------|--------------------------------------|--------------------------|
| Verse            | `{book}-{chapter}-{verse}-web.mp3`   | `genesis-1-1-web.mp3`    |
| Chapter          | `chapter-{N}.mp3`                    | `chapter-1.mp3`          |
| Book release     | `{book}-complete.mp3`                | `genesis-complete.mp3`   |
| Chapter sidecar  | `{book}-chapters.json`               | `genesis-chapters.json`  |

## Requirements

- Python 3.8+
- ffmpeg (for the concat demuxer)
- Venice API key (env `VENICE_API_KEY` or `~/.openclaw/openclaw.json`)
- `gh` CLI authenticated to push releases (used by `release-book.py`)

## ffmpeg concatenation

Lossless stitching via the concat demuxer:

```bash
# Verses → chapter
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy chapter-N.mp3

# Chapters → book
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy book-complete.mp3
```

Per-verse files are deleted after a successful chapter stitch to save space.

## Web player

The Astro static site lives in `web/` and deploys to GitHub Pages at [✝.fm](https://xn--pci.fm). It reads `web/src/data/books.json` for the index, fetches the chapter sidecar at build time for each released book, and exposes the podcast RSS at `/feed.xml`. See [`web/README.md`](web/README.md) for local dev, deploy, and the data contract.

## Current progress

See [`state/progress.json`](state/progress.json) — book, chapter, verse pointer plus the list of completed chapters. The web home page mirrors this in real time once the daily commit triggers a Pages rebuild.
