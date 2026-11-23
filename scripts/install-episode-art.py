#!/usr/bin/env python3
"""Install a book's square painting as episode art.

Reads the square master assets/book-art/{slug}.jpg and writes:
  web/public/book-art/{slug}-square.jpg   the master's own square, RSS itunes:image
  web/public/book-art/{slug}.jpg          1920x1080, book page and og:image
  web/public/book-art/{slug}-thumb.jpg    144x80, books-page card

The master must be square and at least MIN_SIDE pixels; anything else stops
the script, because podcast apps show the square as the episode tile.

The paintings are die-cut stickers on a plain cream background, so the wide
image is the whole sticker centred on a canvas of that same cream, and the
thumbnail is a 16:9 crop from the middle of the scene. Nothing is upscaled.
"""
import sys
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets" / "book-art"
PUB = ROOT / "web" / "public" / "book-art"

MIN_SIDE = 1400  # Apple's minimum for episode art
MAX_SIDE = 3000  # Apple's and Spotify's largest size
SQUARE_MAX_BYTES = 500 * 1024  # feed validators warn above about 500 KB
WIDE = (1920, 1080)
THUMB = (144, 80)
THUMB_CROP = 0.62  # share of the square's width the thumbnail crop spans


def load_master(src: Path) -> Image.Image:
    if not src.exists():
        raise SystemExit(f"missing {src}")
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w != h:
        raise SystemExit(f"{src.name} is {w}x{h}; the master must be square")
    if w < MIN_SIDE:
        raise SystemExit(f"{src.name} is {w}x{h}; the master must be at least {MIN_SIDE}x{MIN_SIDE}")
    if w > MAX_SIDE:
        im = im.resize((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return im


def background(im: Image.Image) -> tuple[int, ...]:
    """The cream around the sticker, averaged from the four corners."""
    w, h = im.size
    n = max(8, w // 64)
    boxes = [(0, 0, n, n), (w - n, 0, w, n), (0, h - n, n, h), (w - n, h - n, w, h)]
    means = [ImageStat.Stat(im.crop(box)).mean for box in boxes]
    return tuple(round(sum(m[i] for m in means) / len(means)) for i in range(3))


def wide(im: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", WIDE, background(im))
    side = WIDE[1]
    sticker = im.resize((side, side), Image.Resampling.LANCZOS) if im.width != side else im
    canvas.paste(sticker, ((WIDE[0] - side) // 2, 0))
    return canvas


def thumb(im: Image.Image) -> Image.Image:
    w = round(im.width * THUMB_CROP)
    h = round(w * THUMB[1] / THUMB[0])
    left = (im.width - w) // 2
    top = (im.height - h) // 2
    return im.crop((left, top, left + w, top + h)).resize(THUMB, Image.Resampling.LANCZOS)


def save_under(im: Image.Image, path: Path, max_bytes: int) -> int:
    for quality in (90, 86, 82, 78, 74, 70):
        im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
        if path.stat().st_size <= max_bytes:
            return quality
    raise SystemExit(f"{path.name} is still {path.stat().st_size // 1024} KB at quality 70")


def install(slug: str) -> None:
    im = load_master(ART / f"{slug}.jpg")
    PUB.mkdir(parents=True, exist_ok=True)
    sq = PUB / f"{slug}-square.jpg"
    q = save_under(im, sq, SQUARE_MAX_BYTES)
    wide_path = PUB / f"{slug}.jpg"
    wide(im).save(wide_path, "JPEG", quality=86, optimize=True, progressive=True)
    thumb_path = PUB / f"{slug}-thumb.jpg"
    thumb(im).save(thumb_path, "JPEG", quality=84, optimize=True)
    print(f"installed {slug}: {sq.name} {im.width}x{im.height} q{q}, {wide_path.name} {WIDE[0]}x{WIDE[1]}, {thumb_path.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: install-episode-art.py <slug> [slug...]")
    for slug in sys.argv[1:]:
        install(slug)
