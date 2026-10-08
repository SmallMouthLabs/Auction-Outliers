"""Synthetic placeholder images for DEMO MODE. Every image is watermarked 'DEMO FIXTURE - SYNTHETIC'."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

PALETTES = {
    "clothing": [(94, 72, 58), (168, 128, 92), (60, 70, 90), (120, 40, 40)],
    "jewelry": [(200, 200, 205), (180, 150, 70), (90, 90, 95), (40, 110, 120)],
}


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def synthetic_image(title: str, domain: str, index: int, detail_text: str | None = None, size: int = 900) -> bytes:
    pal = PALETTES.get(domain, PALETTES["clothing"])
    bg = pal[index % len(pal)]
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    # simple "garment / jewelry" silhouette so images are not identical blocks
    if domain == "jewelry":
        d.ellipse((size * 0.25, size * 0.2, size * 0.75, size * 0.7), outline=(240, 230, 200), width=18)
        d.ellipse((size * 0.45, size * 0.62, size * 0.55, size * 0.72), fill=(240, 230, 200))
    else:
        d.polygon([(size * 0.3, size * 0.2), (size * 0.7, size * 0.2), (size * 0.85, size * 0.35), (size * 0.75, size * 0.42),
                   (size * 0.72, size * 0.85), (size * 0.28, size * 0.85), (size * 0.25, size * 0.42), (size * 0.15, size * 0.35)],
                  outline=(235, 225, 210), width=14)
    if detail_text:
        # a small "label" with text to give the zoom tool something to look at
        box = (int(size * 0.38), int(size * 0.5), int(size * 0.62), int(size * 0.6))
        d.rectangle(box, fill=(245, 240, 225), outline=(30, 30, 30), width=2)
        f = _font(16)
        d.text((box[0] + 8, box[1] + 10), detail_text[:40], fill=(20, 20, 20), font=f)
    f_big = _font(40)
    f_small = _font(22)
    d.text((30, 30), "DEMO FIXTURE", fill=(255, 255, 255), font=f_big)
    d.text((30, 80), "SYNTHETIC IMAGE - NOT A REAL LISTING PHOTO", fill=(255, 255, 255), font=f_small)
    d.text((30, size - 70), f"{title[:48]}  |  image {index}", fill=(255, 255, 255), font=f_small)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
