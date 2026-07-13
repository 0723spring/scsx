"""OCR 识别服务文件。

文件职责：
1. 提供 run_ocr(image_path) 统一入口。
2. 第一阶段实现 mock OCR，返回 OCR 文本和 box。
3. 第二阶段预留 PaddleOCR 接入位置。
4. 将 OCR 原始结果转换为统一格式：
   [{"text": "...", "confidence": 0.98, "box": [[x1,y1], ...]}]
5. 支持后续通过配置切换 mock 模式和 paddle 模式。
6. OCR 异常时抛出明确错误，交给 main.py 统一返回。
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import LABEL_DIR


def to_quad(box: list[int]) -> list[list[int]]:
    x1, y1, x2, y2 = box
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


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
    for name in ["labels_clean.json", "labels_augmented.json", "labels.json"]:
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
            "box": to_quad(box) if box else None,
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


def run_ocr(image_path: str | Path, original_filename: str | None = None) -> list[dict[str, Any]]:
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
