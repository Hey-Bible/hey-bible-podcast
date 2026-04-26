# WEB Bible Audio Project

Complete audio Bible using ElevenLabs Bill voice via Venice AI TTS.

## Structure

```
books/
├── genesis/
│   ├── 1/
│   │   ├── genesis-1-1-web.mp3
│   │   ├── genesis-1-2-web.mp3
│   │   └── ...
│   ├── 2/
│   └── ...
├── exodus/
└── ...
```

## Stats

- **Total verses:** 31,417
- **Daily batch:** 50 verses
- **Estimated completion:** ~1.7 years
- **Voice:** ElevenLabs Bill (via Venice TTS)
- **Translation:** WEB (World English Bible)

## Cron Schedule

Runs daily at 7:00 PM EST via `scripts/run-daily.sh`

## Manual Run

```bash
cd ~/.openclaw/workspace-claudius/web-bible-audio
python3 scripts/generate-verses.py
```

## State Tracking

Progress tracked in `state/progress.json`:
- Current book/chapter/verse
- Completed verse count
- Last run timestamp

## File Naming Convention

`{book}-{chapter}-{verse}-web.mp3`

Example: `genesis-1-1-web.mp3`
