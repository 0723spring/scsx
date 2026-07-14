"""OCR service with mock fallback and optional PaddleOCR integration."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import LABEL_DIR, OCR_MODE


def to_quad(box: list[int]) -> list[list[int]]:
    x1, y1, x2, y2 = box
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def normalize_point(point: Any) -> list[int]:
    return [int(round(float(point[0]))), int(round(float(point[1])))]


def normalize_poly(poly: Any) -> list[list[int]] | None:
    if poly is None:
        return None
    if hasattr(poly, "tolist"):
        poly = poly.tolist()
    if len(poly) < 4:
        return None
    return [normalize_point(point) for point in poly[:4]]


def union_boxes(*boxes: list[int] | None) -> list[int] | None:
    valid = [box for box in boxes if box]
    if not valid:
        return None
    return [
        min(box[0] for box in valid),
        min(box[1] for box in valid),
        max(box[2] for box in valid),
        max(box[3] for box in valid),
    ]


@lru_cache(maxsize=1)
def load_label_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for name in ["labels_clean.json", "labels_augmented.json", "labels_rotated.json", "labels.json"]:
        path = LABEL_DIR / name
        if not path.exists():
            continue
        labels = json.loads(path.read_text(encoding="utf-8"))
        for item in labels:
            image_name = Path(item["image"]).name
            index[image_name] = item
    return index


def label_to_ocr(label: dict[str, Any]) -> list[dict[str, Any]]:
    fields = label["fields"]
    boxes = label.get("main_boxes", {})
    boxes_valid = label.get("metadata", {}).get("boxes_valid", True)
    receiver_identity_box = union_boxes(boxes.get("receiver_name"), boxes.get("receiver_phone"))
    sender_identity_box = union_boxes(boxes.get("sender_name"), boxes.get("sender_phone"))

    ocr_items = [
        ("运单号：" + fields["tracking_number"], boxes.get("tracking_number"), 0.99),
        ("收方地址：" + fields["receiver_address"], boxes.get("receiver_address"), 0.98),
        (f"收方：{fields['receiver_name']} {fields['receiver_phone']}", receiver_identity_box, 0.98),
        ("寄方地址：" + fields["sender_address"], boxes.get("sender_address"), 0.96),
        (f"寄方：{fields['sender_name']} {fields['sender_phone']}", sender_identity_box, 0.96),
    ]

    results = []
    for text, box, confidence in ocr_items:
        results.append({
            "text": text,
            "confidence": confidence,
            "box": to_quad(box) if box and boxes_valid else None,
        })
    return results


def default_mock_ocr() -> list[dict[str, Any]]:
    return [
        {
            "text": "运单号：81793571802948",
            "confidence": 0.99,
            "box": to_quad([285, 336, 564, 362]),
        },
        {
            "text": "收方地址：重庆市重庆市渝北区金开大道168号星光公寓6栋2100室",
            "confidence": 0.98,
            "box": to_quad([160, 472, 1000, 506]),
        },
        {
            "text": "收方：吕俊峰 13687105423",
            "confidence": 0.98,
            "box": to_quad([160, 563, 522, 596]),
        },
    ]


@lru_cache(maxsize=1)
def get_paddle_ocr() -> Any:
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError("PaddleOCR 未安装，请先安装 requirements-ocr.txt") from exc

    return PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _get_sequence(result: dict[str, Any], key: str) -> list[Any]:
    value = result.get(key, [])
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value)


def paddle_to_ocr_items(paddle_results: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for page in paddle_results:
        page_result = dict(page)
        texts = _get_sequence(page_result, "rec_texts")
        scores = _get_sequence(page_result, "rec_scores")
        polys = _get_sequence(page_result, "rec_polys")
        if not polys:
            polys = _get_sequence(page_result, "dt_polys")

        for index, text in enumerate(texts):
            text = str(text).strip()
            if not text:
                continue
            confidence = float(scores[index]) if index < len(scores) else 0.0
            box = normalize_poly(polys[index]) if index < len(polys) else None
            normalized.append({
                "text": text,
                "confidence": confidence,
                "box": box,
            })
    return normalized


def run_paddle_ocr(image_path: str | Path) -> list[dict[str, Any]]:
    ocr = get_paddle_ocr()
    results = ocr.predict(str(image_path))
    return paddle_to_ocr_items(results)


def run_mock_ocr(image_path: str | Path, original_filename: str | None = None) -> list[dict[str, Any]]:
    match_names = []
    if original_filename:
        match_names.append(Path(original_filename).name)
    match_names.append(Path(image_path).name)

    index = load_label_index()
    for name in match_names:
        label = index.get(name)
        if label:
            return label_to_ocr(label)

    return default_mock_ocr()


def run_ocr(image_path: str | Path, original_filename: str | None = None) -> list[dict[str, Any]]:
    if OCR_MODE == "paddle":
        return run_paddle_ocr(image_path)

    if OCR_MODE == "auto":
        try:
            paddle_results = run_paddle_ocr(image_path)
            if paddle_results:
                return paddle_results
        except Exception:
            pass

    return run_mock_ocr(image_path, original_filename=original_filename)
