"""Tests for install-episode-art.py.

Run from the repo root: python3 -m unittest discover -s scripts -p 'test_*.py'
(needs Pillow).
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

spec = importlib.util.spec_from_file_location("install_episode_art", Path(__file__).with_name("install-episode-art.py"))
assert spec and spec.loader
art: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)

CREAM = (238, 225, 206)


def sticker(side: int) -> Image.Image:
    """A cream square with a coloured block in the middle, like a sticker painting."""
    im = Image.new("RGB", (side, side), CREAM)
    m = side // 5
    im.paste((90, 120, 80), (m, m, side - m, side - m))
    return im


class InstallEpisodeArtTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.art_dir, self.pub_dir = root / "art", root / "pub"
        self.art_dir.mkdir()
        self._saved = art.ART, art.PUB
        art.ART, art.PUB = self.art_dir, self.pub_dir

    def tearDown(self):
        art.ART, art.PUB = self._saved
        self.tmp.cleanup()

    def write_master(self, im: Image.Image, slug: str = "ruth") -> None:
        im.save(self.art_dir / f"{slug}.jpg", "JPEG", quality=95)

    def test_writes_native_square_wide_and_thumb(self):
        self.write_master(sticker(2048))
        art.install("ruth")
        sq = Image.open(self.pub_dir / "ruth-square.jpg")
        self.assertEqual(sq.size, (2048, 2048))
        self.assertLessEqual((self.pub_dir / "ruth-square.jpg").stat().st_size, art.SQUARE_MAX_BYTES)
        self.assertEqual(Image.open(self.pub_dir / "ruth.jpg").size, art.WIDE)
        self.assertEqual(Image.open(self.pub_dir / "ruth-thumb.jpg").size, art.THUMB)

    def test_square_is_not_letterboxed(self):
        self.write_master(sticker(2048))
        art.install("ruth")
        sq = Image.open(self.pub_dir / "ruth-square.jpg").convert("RGB")
        # The middle of the top and bottom edges is the master's own cream, not a blurred band.
        for xy in [(1024, 10), (1024, 2037)]:
            for got, want in zip(sq.getpixel(xy), CREAM):
                self.assertAlmostEqual(got, want, delta=6)

    def test_wide_sides_match_the_cream_background(self):
        self.write_master(sticker(2048))
        art.install("ruth")
        wide = Image.open(self.pub_dir / "ruth.jpg").convert("RGB")
        for xy in [(20, 540), (1900, 540)]:
            for got, want in zip(wide.getpixel(xy), CREAM):
                self.assertAlmostEqual(got, want, delta=6)

    def test_thumb_comes_from_the_middle_of_the_scene(self):
        self.write_master(sticker(2048))
        art.install("ruth")
        red = Image.open(self.pub_dir / "ruth-thumb.jpg").convert("RGB").getpixel((72, 40))[0]
        self.assertLess(red, 130)  # the green block, not the cream margin

    def test_rejects_a_wide_master(self):
        self.write_master(Image.new("RGB", (1280, 720), CREAM))
        with self.assertRaises(SystemExit) as e:
            art.install("ruth")
        self.assertIn("must be square", str(e.exception))

    def test_rejects_a_small_master(self):
        self.write_master(sticker(1024))
        with self.assertRaises(SystemExit) as e:
            art.install("ruth")
        self.assertIn("at least 1400", str(e.exception))

    def test_shrinks_a_master_above_3000(self):
        self.write_master(sticker(3200))
        art.install("ruth")
        self.assertEqual(Image.open(self.pub_dir / "ruth-square.jpg").size, (3000, 3000))

    def test_missing_master(self):
        with self.assertRaises(SystemExit) as e:
            art.install("obadiah")
        self.assertIn("missing", str(e.exception))


if __name__ == "__main__":
    unittest.main()
