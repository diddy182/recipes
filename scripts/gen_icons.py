#!/usr/bin/env python3
"""Generate PWA app icons + favicon for the recipe site.

Editorial look: near-black (#1a1a1a) field with a cream serif monogram "JR".
Run once (or after changing the design). Outputs into site/icons + favicon.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "site" / "icons"
ICONS.mkdir(parents=True, exist_ok=True)

INK = (26, 26, 26)       # #1a1a1a
CREAM = (250, 247, 242)  # warm off-white

SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Georgia.ttf",
]


def load_serif(size):
    for p in SERIF_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_icon(size, maskable=False, text="JR"):
    img = Image.new("RGB", (size, size), INK)
    d = ImageDraw.Draw(img)
    # Maskable icons need the glyph inside a safe zone (~80% center).
    scale = 0.42 if maskable else 0.52
    font = load_serif(int(size * scale))
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    d.text((x, y), text, font=font, fill=CREAM)
    return img


for s in (32, 180, 192, 512):
    make_icon(s).save(ICONS / f"icon-{s}.png")
make_icon(512, maskable=True).save(ICONS / "icon-maskable-512.png")
# favicon.ico (multi-size)
make_icon(64).save(ROOT / "site" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
print("icons written to", ICONS)
