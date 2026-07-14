"""Image preprocessing helpers for uploaded waybill images."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image, ImageOps

from .config import OUTPUT_DIR
from .file_utils import output_url


MAX_DESKEW_ANGLE = 8.0
MIN_APPLY_ANGLE = 0.35


def _threshold_dark_pixels(gray: Image.Image) -> np.ndarray:
    array = np.asarray(gray, dtype=np.uint8)
    threshold = max(80, min(210, int(array.mean() - array.std() * 0.15)))
    return array < threshold


def _rotate_mask(mask: np.ndarray, angle: float) -> np.ndarray:
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    rotated = image.rotate(angle, expand=True, fillcolor=0, resample=Image.Resampling.BILINEAR)
    return np.asarray(rotated) > 0


def _projection_score(mask: np.ndarray) -> float:
    if mask.sum() == 0:
        return 0.0
    row_counts = mask.sum(axis=1).astype(np.float64)
    return float(row_counts.var())


def estimate_skew_angle(image_path: str | Path) -> float:
    """Estimate the clockwise skew angle of a mostly horizontal text image.

    A lightweight projection search is used instead of a hard OpenCV dependency,
    so the base project can run after installing only requirements.txt.
    """

    with Image.open(image_path) as image:
        gray = ImageOps.grayscale(image)
        gray.thumbnail((1100, 1100))
        mask = _threshold_dark_pixels(gray)

    if mask.sum() < 100:
        return 0.0

    candidates = np.arange(-MAX_DESKEW_ANGLE, MAX_DESKEW_ANGLE + 0.001, 0.5)
    best_angle = 0.0
    best_score = -1.0
    for angle in candidates:
        score = _projection_score(_rotate_mask(mask, float(angle)))
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    fine_candidates = np.arange(best_angle - 0.5, best_angle + 0.501, 0.1)
    for angle in fine_candidates:
        if angle < -MAX_DESKEW_ANGLE or angle > MAX_DESKEW_ANGLE:
            continue
        score = _projection_score(_rotate_mask(mask, float(angle)))
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    return round(best_angle, 2)


def _save_preprocessed(image_path: Path, angle: float) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as image:
        corrected = image.convert("RGB").rotate(
            angle,
            expand=True,
            fillcolor=(255, 255, 255),
            resample=Image.Resampling.BICUBIC,
        )
        output_path = OUTPUT_DIR / f"preprocessed_{uuid4().hex[:12]}.png"
        corrected.save(output_path)
    return output_path


def preprocess_image(image_path: str | Path, enable_preprocess: bool = False) -> dict:
    """Optionally deskew an image and return the path used by OCR."""

    source_path = Path(image_path)
    base_result = {
        "image_path": source_path,
        "preprocessed_image_url": None,
        "preprocess": {
            "enabled": bool(enable_preprocess),
            "applied": False,
            "angle": 0.0,
            "message": "preprocess disabled",
        },
    }
    if not enable_preprocess:
        return base_result

    angle = estimate_skew_angle(source_path)
    base_result["preprocess"]["angle"] = angle
    if abs(angle) < MIN_APPLY_ANGLE:
        base_result["preprocess"]["message"] = "image is already close to horizontal"
        return base_result

    corrected_path = _save_preprocessed(source_path, angle)
    base_result["image_path"] = corrected_path
    base_result["preprocessed_image_url"] = output_url(corrected_path)
    base_result["preprocess"]["applied"] = True
    base_result["preprocess"]["message"] = "deskew correction applied"
    return base_result
