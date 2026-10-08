"""Image loading, resizing, hashing and crop/zoom helpers (Pillow)."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from ..config import get_settings
from ..providers.base import ImageInput

MEDIA = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def to_jpeg_bytes(img: Image.Image, max_px: int, quality: int = 88) -> bytes:
    im = img.copy()
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def prepare_inputs(local_paths: list[str], max_px: int, limit: int) -> list[ImageInput]:
    """Load up to `limit` images from disk and downscale for a model call."""
    out: list[ImageInput] = []
    data_dir = get_settings().data_dir
    for i, rel in enumerate(local_paths[:limit]):
        p = data_dir / rel
        if not p.exists():
            continue
        img = load_image(p)
        out.append(ImageInput(data=to_jpeg_bytes(img, max_px), media_type="image/jpeg", label=f"listing photo {i}", index=i))
    return out


def make_zoom(local_paths: list[str], max_px: int = 1200):
    """Return a zoom function usable as a provider tool."""
    data_dir = get_settings().data_dir

    def zoom(req: dict[str, Any]) -> ImageInput:
        idx = int(req["image_index"])
        if idx < 0 or idx >= len(local_paths):
            raise ValueError(f"image_index {idx} out of range (0-{len(local_paths)-1})")
        img = load_image(data_dir / local_paths[idx])
        W, H = img.size
        x, y, w, h = float(req["x"]), float(req["y"]), float(req["w"]), float(req["h"])
        x = min(max(x, 0.0), 0.99)
        y = min(max(y, 0.0), 0.99)
        w = min(max(w, 0.02), 1.0 - x)
        h = min(max(h, 0.02), 1.0 - y)
        box = (int(x * W), int(y * H), int((x + w) * W), int((y + h) * H))
        crop = img.crop(box)
        # upscale small crops so text is legible
        if max(crop.size) < 600:
            scale = 600 / max(crop.size)
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
        return ImageInput(data=to_jpeg_bytes(crop, max_px, quality=92), media_type="image/jpeg", label=f"zoom of image {idx}", index=idx)

    return zoom


def image_dims(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size
