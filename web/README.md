# ✝.fm — The Hey Bible Podcast web player

Astro 5 static site for the Hey Bible podcast. Streams each released book in-browser with chapter seek, indexes all 66 books, and exposes a Podcasting 2.0 RSS feed at `/feed.xml`.

## Stack

- **Astro 5** with static export (`output: 'static'`, trailing-slash directories)
- **Tailwind CSS v4** via `@tailwindcss/vite`
- **Native `<audio>`** element with timestamp-based chapter seeking
- **Nunito** from Google Fonts
- 3-mode theme toggle (light / dark / system) via `localStorage` + `<html data-theme>`

## Local dev

```sh
cd web
npm install
npm run dev   # http://localhost:4321
```

## Build

```sh
npm run build      # outputs to web/dist
npm run preview    # serves dist locally
```

## Deploy

Cloudflare Pages, building directly from the GitHub repo. One-time setup:

1. In the Cloudflare dashboard: **Workers & Pages → Create → Pages → Connect to Git**, select this repo.
2. **Build configuration:**
   - Framework preset: **Astro**
   - Build command: `cd web && npm ci && npm run build`
   - Build output directory: `web/dist`
   - Root directory: leave blank (project root)
3. **Custom domain:** add `podcast.heybible.org` to the Pages project (canonical). Brand domain `✝.fm` (`xn--pci.fm`) lives in a separate Cloudflare zone and 301-redirects here.
4. Pushing to `master` rebuilds automatically; PRs get preview deployments.

## Data contract

The Python pipeline (`scripts/compile-book.py`, `scripts/release-book.py`) is responsible for emitting two assets per release:

- `{book}-complete.mp3` — full book audio
- `{book}-chapters.json` — chapter offsets (sidecar)

Sidecar schema:

```json
{
  "book": "genesis",
  "title": "Genesis",
  "duration": 12345.67,
  "releaseTag": "genesis-2026-05",
  "chapters": [
    { "number": 1, "title": "Chapter 1", "start": 0, "end": 234.5, "duration": 234.5 }
  ]
}
```

After uploading both assets to R2, `release-book.py` should:

1. Edit `web/src/data/books.json`, set the book's `status: "available"`, `releaseTag`, `releaseSize` (in bytes).
2. Commit & push — the deploy workflow rebuilds the site, which fetches the sidecar JSON at build time and bakes chapter offsets into the static HTML.

The R2 base URL is hard-coded in `src/lib/books.ts` as `R2_PUBLIC_BASE`. Update it if the bucket's custom domain changes. Audio uploads must set `Content-Type: audio/mpeg` and `Content-Disposition: inline` — see the root README for the R2 credential setup.

## File map

```
web/
├── astro.config.mjs       site = https://podcast.heybible.org
├── public/
│   ├── favicon.svg
│   └── robots.txt
└── src/
    ├── data/
    │   ├── books.json     66 books, status, progress
    │   └── subscribe.json Apple/Spotify/Overcast URLs (placeholders)
    ├── lib/
    │   ├── books.ts       typed loaders + URL builders
    │   └── chapters.ts    build-time sidecar fetcher
    ├── styles/global.css  @theme + wave SVG bg
    ├── layouts/Base.astro
    ├── components/
    │   ├── Header.astro   sticky nav + 3-mode theme toggle
    │   ├── Footer.astro
    │   ├── ThemeScript.astro  pre-paint to avoid FOUC
    │   ├── BookCard.astro
    │   ├── ChapterPlayer.astro  <audio> + seek buttons
    │   └── SubscribeLinks.astro
    └── pages/
        ├── index.astro
        ├── books/index.astro
        ├── books/[book].astro
        └── feed.xml.ts    podcast RSS endpoint
```
