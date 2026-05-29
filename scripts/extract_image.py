#!/usr/bin/env python3
"""Extract the hero photo from a recipe PDF.

Picks the largest raster image embedded in the PDF (recipe photos are always
the biggest image; logos/icons are tiny) and saves it as a web-friendly JPEG.

Usage: extract_image.py <pdf_path> <out_jpg> [--max 1200]
"""
import sys
import io
import argparse
import fitz  # PyMuPDF
from PIL import Image, ImageStat


def _is_real_photo(pil: Image.Image) -> bool:
    """Reject solid-color masks, gradients, and near-flat overlays that PDFs
    embed alongside real photos. A genuine food photo has meaningful color
    variance; a black/white mask has almost none."""
    rgb = pil.convert("RGB")
    # Downsample for a fast variance check.
    small = rgb.copy()
    small.thumbnail((100, 100))
    stat = ImageStat.Stat(small)
    avg_stddev = sum(stat.stddev) / len(stat.stddev)
    if avg_stddev < 14:  # near-uniform → mask/overlay, not a photo
        return False
    # Reject banner-ish strips (logos, dividers).
    ratio = max(pil.width, pil.height) / max(1, min(pil.width, pil.height))
    if ratio > 3.0:
        return False
    return True


def extract_hero(pdf_path: str, out_path: str, max_dim: int = 1200) -> bool:
    doc = fitz.open(pdf_path)
    best = None  # (pixels, PIL.Image)
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                base = doc.extract_image(xref)
            except Exception:
                continue
            try:
                pil = Image.open(io.BytesIO(base["image"]))
            except Exception:
                continue
            # Ignore tiny images (icons, spacers, bullets).
            if pil.width < 150 or pil.height < 150:
                continue
            if not _is_real_photo(pil):
                continue
            pixels = pil.width * pil.height
            if best is None or pixels > best[0]:
                best = (pixels, pil)
    doc.close()

    if best is None:
        return False

    img = best[1].convert("RGB")
    # Downscale to a sane max dimension while keeping aspect ratio.
    if max(img.width, img.height) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    img.save(out_path, "JPEG", quality=82, optimize=True)
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=1200)
    args = ap.parse_args()
    ok = extract_hero(args.pdf, args.out, args.max)
    if not ok:
        print(f"NO_IMAGE: {args.pdf}", file=sys.stderr)
        sys.exit(2)
    print(f"OK: {args.out}")
