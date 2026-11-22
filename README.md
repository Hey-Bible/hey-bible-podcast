# ✝.fm — The Hey Bible Podcast web player

Astro 5 static site for the Hey Bible podcast. Streams each released book in-browser with chapter seek, indexes all 66 books, and exposes a Podcasting 2.0 RSS feed at `/feed.xml`.

## Stack

- **Astro 5** with static export (`output: 'static'`, trailing-slash directories)
- **Tailwind CSS v4** via `@tailwindcss/vite`
- **Native `<audio>`** element with timestamp-based chapter seeking
- **Storybook Sticker** theme, copied from the Hey Bible app: cream page, brown ink, die-cut cards (see `src/styles/global.css`)
- **Fredoka** (headings) and **Nunito** (body), self-hosted in `public/fonts`
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

Cloudflare Workers Static Assets, built from GitHub. **Production does not build from `master`.**

The full monorepo is multi‑GB (verse/chapter audio in git), so Cloudflare clone/build of `master` times out. Production uses a **web-only branch**:

| Setting | Value |
|--------|--------|
| Production branch | `cf-deploy-web` |
| Root directory | *(empty / repo root of that branch)* — **not** `web` |
| Build command | `npm run build` |
| Build output directory | `dist` |

### Syncing the deploy branch

From the monorepo root after `books.json` / site changes:

```bash
bash scripts/sync-cf-deploy-web.sh
```

`scripts/release-book.py` calls this automatically after committing a release to `master`. If a CF build is stale, re-run the script (or push an empty commit on `cf-deploy-web`).

### One-time CF project setup

1. **Workers & Pages →** podcast worker → **Settings → Build**
2. Production branch `cf-deploy-web`, root directory blank, build `npm run build`, output `dist`
3. Custom domain: `podcast.heybible.org` (canonical). Brand domain `✝.fm` (`xn--pci.fm`) 301-redirects here.
4. Pushing to `cf-deploy-web` rebuilds; do not rely on `master` pushes for deploys.

## Data contract

The Python pipeline (`scripts/compile-book.py`, `scripts/release-book.py`) is responsible for emitting two assets per release:

- `{book}-web.mp3` — full book audio
- `{book}-web.json` — chapter offsets (sidecar)

Sidecar schema:

```json
{
  "book": "genesis",
  "title": "Genesis",
  "duration": 12345.67,
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
├── wrangler.jsonc         Cloudflare Workers Static Assets config
├── scripts/
│   └── og-image.html      source for public/og-image.png
├── public/
│   ├── favicon.svg        the Hey Bible book-and-cross mark
│   ├── og-image.png       1200×630 social preview
│   ├── fonts/             Fredoka + Nunito (variable, latin subset)
│   └── robots.txt
└── src/
    ├── data/
    │   ├── books.json     66 books, status, progress
    │   └── subscribe.json Apple/Spotify/Overcast URLs (placeholders)
    ├── lib/
    │   ├── books.ts       typed loaders + URL builders
    │   └── chapters.ts    build-time sidecar fetcher
    ├── styles/global.css  theme tokens (light + night) and component styles
    ├── layouts/Base.astro
    ├── components/
    │   ├── Header.astro   sticky nav + 3-mode theme toggle
    │   ├── Logo.astro     mark + wordmark lockup
    │   ├── Sticker.astro  sheep / sun / moon decoration
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

## Theme

The look is the Hey Bible app's Storybook Sticker theme: a cream page, brown ink, terracotta buttons and links, and cards cut out with a white edge and a soft shadow. Dark mode is the same sheet at night, on an indigo sky with cream edges.

- The tokens live at the top of `src/styles/global.css`. `--color-retro-*` are the page, text, primary and surface colours; `--sticker-*` are the die-cut edge, the shadows and the pastel tints. Dark mode overrides both sets under `html[data-theme="dark"]`.
- White text goes only on terracotta or darker. Text on a pastel pill is always ink (`--sticker-ink`), in both modes.
- Stickers are accents: at most one `<Sticker>` per page, and none on cards in a list.

### Social preview image

`public/og-image.png` is a screenshot of `scripts/og-image.html`. To regenerate it, from `web/`:

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --screenshot=public/og-image.png --window-size=1200,630 --hide-scrollbars \
  "file://$PWD/scripts/og-image.html"
```
