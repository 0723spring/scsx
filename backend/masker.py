"""String and image privacy masking utilities."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image

from .config import OUTPUT_DIR
from .file_utils import output_url


def mask_name(name: str | None) -> str | None:
    if not name:
        return None
    if len(name) == 1:
        return "*"
    if len(name) == 2:
        return name[0] + "*"
    return name[0] + "*" * (len(name) - 2) + name[-1]


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    if len(phone) != 11:
        return phone
    return phone[:3] + "****" + phone[-4:]


def mask_tracking_number(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def mask_address(address: str | None) -> str | None:
    if not address:
        return None
    region_markers = ["\u533a", "\u53bf", "\u65d7", "\u5e02", "\u5dde", "\u76df"]
    split_at = -1
    for marker in region_markers:
        position = address.find(marker)
        if position >= 2:
            split_at = max(split_at, position)
    if split_at >= 3:
        return address[: split_at + 1] + "**"
    keep = min(max(4, len(address) // 3), 10)
    return address[:keep] + "**"


def quad_to_rect(box: list[list[int]] | None, padding: int = 6) -> list[int] | None:
    if not box:
        return None
    xs = [int(point[0]) for point in box]
    ys = [int(point[1]) for point in box]
    return [min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding]


def _clamp_rect(rect: list[int], width: int, height: int) -> tuple[int, int, int, int] | None:
    left = max(0, min(width, rect[0]))
    top = max(0, min(height, rect[1]))
    right = max(0, min(width, rect[2]))
    bottom = max(0, min(height, rect[3]))
    if right - left < 2 or bottom - top < 2:
        return None
    return left, top, right, bottom


def _mosaic_region(image: Image.Image, rect: tuple[int, int, int, int], block_size: int = 12) -> None:
    left, top, right, bottom = rect
    region = image.crop(rect)
    small_width = max(1, (right - left) // block_size)
    small_height = max(1, (bottom - top) // block_size)
    small = region.resize((small_width, small_height), resample=Image.Resampling.BILINEAR)
    mosaic = small.resize(region.size, resample=Image.Resampling.NEAREST)
    image.paste(mosaic, rect)


def is_sensitive_text(text: str, fields: dict) -> bool:
    sensitive_values = [
        fields.get("raw_receiver_name"),
        fields.get("raw_phone"),
        fields.get("raw_address"),
        fields.get("raw_tracking_number"),
        fields.get("receiver_name"),
        fields.get("phone"),
        fields.get("address"),
        fields.get("tracking_number"),
    ]
    if any(value and value in text for value in sensitive_values):
        return True

    keywords = [
        "\u6536\u65b9",
        "\u6536\u4ef6\u4eba",
        "\u6536\u8d27\u4eba",
        "\u5bc4\u65b9",
        "\u7535\u8bdd",
        "\u624b\u673a",
        "\u5730\u5740",
        "\u8fd0\u5355\u53f7",
        "\u5feb\u9012\u5355\u53f7",
        "\u5355\u53f7",
    ]
    return any(keyword in text for keyword in keywords)


def mask_sensitive_info(image_path: str | Path, ocr_results: list[dict], fields: dict) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(image_path).convert("RGB")

    for item in ocr_results:
        text = str(item.get("text", ""))
        if not is_sensitive_text(text, fields):
            continue
        rect = quad_to_rect(item.get("box"))
        if not rect:
            continue
        clamped = _clamp_rect(rect, image.width, image.height)
        if clamped:
            _mosaic_region(image, clamped)

    output_path = OUTPUT_DIR / f"masked_{uuid4().hex[:12]}.png"
    image.save(output_path)
    return output_url(output_path)
