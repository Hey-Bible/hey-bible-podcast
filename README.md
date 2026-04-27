# Hey Bible Podcast

The whole Bible read aloud, one book at a time. Audio generated with the ElevenLabs Bill voice via Venice AI TTS, published as a monthly podcast at [podcast.heybible.org](https://podcast.heybible.org) (also reachable at the brand URL [✝.fm](https://xn--pci.fm)).

- **Audio pipeline** (Python) — generates verses daily, stitches chapters as they fill in, compiles each book monthly, uploads each release to Cloudflare R2 on the 1st.
- **Web player** (Astro + Tailwind v4 in `web/`) — static site at ✝.fm with per-book pages, chapter seek, and a Podcasting 2.0 RSS feed.

## Project Structure

```
hey-bible-podcast/
├── verses/                 # Individual verse audio files (deleted after chapter stitch)
│   └── {book}/{chapter}/{book}-{chapter}-{verse}-web.mp3
├── chapters/               # Stitched chapter audio files
│   └── {book}/{book}-{N}-web.mp3
├── assets/titles/          # Pre-generated "Chapter N" audio clips (1–150)
├── intermediate/           # Compiled book + chapter sidecar (monthly 25th, pre-release)
│   ├── {book}-web.mp3
│   └── {book}-web.json
├── scripts/                # Audio pipeline
│   ├── generate-verses.py          # Daily: 50 verses + chapter stitch
│   ├── generate-chapter-titles.py  # One-time: Chapter 1–150 clips
│   ├── compile-book.py             # Monthly 25th: stitch chapters → book + sidecar JSON
│   ├── release-book.py             # Monthly 1st: upload to R2, patch books.json
│   ├── bible_data.py               # 66-book chapter/verse counts
│   └── run-daily.sh                # Cron wrapper
├── state/
│   └── progress.json       # Current book/chapter/verse, completed chapters
└── web/                    # Astro site (deployed by Cloudflare Workers Static Assets) — see web/README.md
```

## Stats

- **Total verses:** 31,417
- **Daily batch:** 50 verses
- **Estimated completion:** ~1.7 years
- **Voice:** ElevenLabs Bill (via Venice TTS)
- **Translation:** [World English Bible](https://worldenglish.bible) — public domain

## Acknowledgments

- **[bible-api.com](https://bible-api.com)** by [Tim Morgan](https://timmorgan.dev) — free API service providing WEB Bible verse text. Source code and open data available on [GitHub](https://github.com/seven1m/bible_api).

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
- Stitch: book-title + (chapter-title-N + chapter-N) for every chapter, into `intermediate/{book}-web.mp3`
- Emit `intermediate/{book}-web.json` — a chapter sidecar with start/end offsets in seconds
- Upload the MP3 + sidecar to Cloudflare R2 so the file is reachable for preview before the 1st-of-month release. The website doesn't surface it yet (status is still `in-progress`), so the URL is "unlisted" — only an operator with the link can hear it.
- Print the review URLs (`audio.heybible.org/{book}-web.mp3` + `…-web.json`)

### Monthly 1st — `scripts/release-book.py`
- Upload `intermediate/{book}-web.mp3` and `intermediate/{book}-web.json` to Cloudflare R2 via `boto3` (S3-compatible API), with `Content-Type: audio/mpeg` / `application/json` and `Content-Disposition: inline` so iOS Safari will stream the MP3 instead of trying to download it
- Patch `web/src/data/books.json`: set the book's `status: "available"`, `releaseTag`, and `releaseSize` (bytes)
- Commit and push — that push triggers a Cloudflare Workers build, which rebuilds the site with the new release

## Audio hosting (Cloudflare R2)

The `<audio>` URL is built from a single constant, `R2_PUBLIC_BASE` in `web/src/lib/books.ts`. Set it to the bucket's custom domain (e.g. `https://audio.heybible.org`) once the bucket is live.

One-time setup:

1. Create an R2 bucket (e.g. `hey-bible-audio`) and attach a custom domain in the Cloudflare dashboard.
2. Create an R2 API token (Object Read & Write, scoped to the bucket); save the Account ID, Access Key ID, and Secret Access Key.
3. Both `compile-book.py` and `release-book.py` upload to R2, so both crons need these env vars set:
   - `R2_ACCOUNT_ID`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET_NAME`

`release-book.py` sets `Content-Type: audio/mpeg` and `Content-Disposition: inline` per upload — both are required for in-browser playback on mobile, since GitHub Releases serves `application/octet-stream` + `attachment` and iOS Safari refuses to stream that.

## Chapter sidecar JSON

`{book}-web.json` is uploaded to R2 alongside `{book}-web.mp3` and is used both by the web chapter player and by the `<podcast:chapters>` link in the RSS feed (Apple Podcasts / Overcast / Pocket Casts render it as the chapter list).

```json
{
  "book": "genesis",
  "title": "Genesis",
  "duration": 12345.67,
  "chapters": [
    { "number": 1, "title": "Chapter 1", "start": 0,     "end": 240.5,  "duration": 240.5 },
    { "number": 2, "title": "Chapter 2", "start": 240.5, "end": 495.1,  "duration": 254.6 }
  ]
}
```

One entry per chapter — `start` is the offset of the spoken "Chapter N" intro, `end` is where the chapter content finishes.

## Manual Commands

```bash
python3 scripts/generate-verses.py          # daily
python3 scripts/compile-book.py             # monthly 25th
python3 scripts/release-book.py             # monthly 1st
python3 scripts/generate-chapter-titles.py  # one-time setup
```

## File naming convention

| Kind             | Pattern                              | Example                  |
|------------------|--------------------------------------|--------------------------|
| Verse            | `{book}-{chapter}-{verse}-web.mp3`   | `genesis-1-1-web.mp3`    |
| Chapter          | `{book}-{N}-web.mp3`                 | `genesis-1-web.mp3`      |
| Book release     | `{book}-web.mp3`                     | `genesis-web.mp3`        |
| Chapter sidecar  | `{book}-web.json`                    | `genesis-web.json`       |

## Requirements

- Python 3.8+
- ffmpeg (for the concat demuxer)
- Venice API key (env `VENICE_API_KEY` or `~/.openclaw/openclaw.json`)
- `boto3` (`pip install boto3`) and Cloudflare R2 credentials (used by `release-book.py`)

## ffmpeg concatenation

Lossless stitching via the concat demuxer:

```bash
# Verses → chapter
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy chapter-N.mp3

# Chapters → book
ffmpeg -f concat -safe 0 -i concat.txt -acodec copy book-web.mp3
```

Per-verse files are deleted after a successful chapter stitch to save space.

## Web player

The Astro static site lives in `web/` and deploys to GitHub Pages at [podcast.heybible.org](https://podcast.heybible.org) (also reachable at the brand URL [✝.fm](https://xn--pci.fm)). It reads `web/src/data/books.json` for the index, fetches the chapter sidecar at build time for each released book, and exposes the podcast RSS at `/feed.xml`. See [`web/README.md`](web/README.md) for local dev, deploy, and the data contract.

## Current progress

See [`state/progress.json`](state/progress.json) — book, chapter, verse pointer plus the list of completed chapters. The web home page mirrors this in real time once the daily commit triggers a Pages rebuild.
