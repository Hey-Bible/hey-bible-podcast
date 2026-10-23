#!/usr/bin/env python3
"""Copy a book painting into the site as episode art.

Reads assets/book-art/{slug}.jpg and writes:
  web/public/book-art/{slug}.jpg          landscape, book page
  web/public/book-art/{slug}-square.jpg   1400 square, RSS itunes:image
  web/public/book-art/{slug}-thumb.jpg    144x80, books-page card
"""
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets" / "book-art"
PUB = ROOT / "web" / "public" / "book-art"


def install(slug: str) -> None:
    src = ART / f"{slug}.jpg"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    PUB.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    if im.size != (1280, 720):
        im = im.resize((1280, 720), Image.Resampling.LANCZOS)
    wide = PUB / f"{slug}.jpg"
    im.save(wide, "JPEG", quality=90, optimize=True)
    w, h = im.size
    scale = max(1400 / w, 1400 / h)
    cover = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    left = (cover.width - 1400) // 2
    top = (cover.height - 1400) // 2
    cover = cover.crop((left, top, left + 1400, top + 1400))
    cover = ImageEnhance.Brightness(cover.filter(ImageFilter.GaussianBlur(28))).enhance(0.55)
    sh = int(1400 * h / w)
    sharp = im.resize((1400, sh), Image.Resampling.LANCZOS)
    cover.paste(sharp, (0, (1400 - sh) // 2))
    square = PUB / f"{slug}-square.jpg"
    cover.save(square, "JPEG", quality=88, optimize=True)
    thumb = im.resize((144, 80), Image.Resampling.LANCZOS)
    thumb_path = PUB / f"{slug}-thumb.jpg"
    thumb.save(thumb_path, "JPEG", quality=80, optimize=True)
    print(f"installed {slug} {wide.name} {square.name} {thumb_path.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: install-episode-art.py <slug> [slug...]")
    for slug in sys.argv[1:]:
        install(slug)
