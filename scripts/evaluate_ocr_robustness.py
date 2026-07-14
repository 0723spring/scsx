"""Run PaddleOCR robustness checks on generated waybill datasets."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DATASET_CONFIGS = [
    ("clean", "labels_clean.json", False),
    ("augmented", "labels_augmented.json", False),
    ("rotated_raw", "labels_rotated.json", False),
    ("rotated_preprocessed", "labels_rotated.json", True),
]


def load_labels(filename: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / "dataset" / "labels" / filename
    return json.loads(path.read_text(encoding="utf-8"))


def is_match(actual: str | None, expected: str | None) -> bool:
    if not actual or not expected:
        return False
    return actual == expected or actual in expected or expected in actual


def mark(value: bool) -> str:
    return "Y" if value else "N"


def short_text(value: str | None, limit: int = 18) -> str:
    if not value:
        return "-"
    return value if len(value) <= limit else value[:limit] + "..."


def evaluate(label: dict[str, Any], dataset: str, enable_preprocess: bool) -> dict[str, Any]:
    from backend.services import recognize_waybill

    image_path = PROJECT_ROOT / "dataset" / label["image"]
    expected = label["fields"]
    started_at = time.perf_counter()
    result = recognize_waybill(
        image_path,
        original_filename=Path(label["image"]).name,
        enable_preprocess=enable_preprocess,
    )
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    fields = result["fields"]

    checks = {
        "name_ok": is_match(fields.get("raw_receiver_name"), expected.get("receiver_name")),
        "phone_ok": is_match(fields.get("raw_phone"), expected.get("receiver_phone")),
        "address_ok": is_match(fields.get("raw_address"), expected.get("receiver_address")),
        "tracking_ok": is_match(fields.get("raw_tracking_number"), expected.get("tracking_number")),
    }
    return {
        "dataset": dataset,
        "image": Path(label["image"]).name,
        "preprocess": enable_preprocess,
        "angle": result["preprocess"]["angle"],
        "ocr_count": len(result["ocr_results"]),
        "elapsed_ms": elapsed_ms,
        "raw_receiver_name": fields.get("raw_receiver_name"),
        "raw_phone": fields.get("raw_phone"),
        "raw_address": fields.get("raw_address"),
        "raw_tracking_number": fields.get("raw_tracking_number"),
        **checks,
        "all_ok": all(checks.values()),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    summary: dict[str, dict[str, str]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["dataset"]].append(row)

    for dataset, dataset_rows in grouped.items():
        total = len(dataset_rows)
        summary[dataset] = {
            "samples": str(total),
            "name": f"{sum(row['name_ok'] for row in dataset_rows)}/{total}",
            "phone": f"{sum(row['phone_ok'] for row in dataset_rows)}/{total}",
            "address": f"{sum(row['address_ok'] for row in dataset_rows)}/{total}",
            "tracking": f"{sum(row['tracking_ok'] for row in dataset_rows)}/{total}",
            "all": f"{sum(row['all_ok'] for row in dataset_rows)}/{total}",
        }
    return summary


def render_report(rows: list[dict[str, Any]], mode: str, count: int) -> str:
    summary = summarize(rows)
    lines = [
        "# OCR 接入与鲁棒性测试记录",
        "",
        "## 1. 测试环境",
        "",
        f"- OCR 模式：`{mode}`",
        "- OCR 模型：PaddleOCR 3.7 默认 PP-OCRv6 通用 OCR pipeline",
        "- PaddlePaddle：CPU 推理",
        "- 模型缓存目录：`C:/Users/34566/.paddlex/official_models/`",
        f"- 每组样本数：`{count}`",
        "",
        "## 2. 汇总结果",
        "",
        "| 数据集 | 样本数 | 姓名 | 手机号 | 地址 | 运单号 | 四项全对 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for dataset, item in summary.items():
        lines.append(
            f"| {dataset} | {item['samples']} | {item['name']} | {item['phone']} | "
            f"{item['address']} | {item['tracking']} | {item['all']} |"
        )

    lines.extend([
        "",
        "## 3. 明细结果",
        "",
        "| 数据集 | 图片 | 预处理 | 角度 | OCR 条数 | 姓名 | 手机号 | 地址 | 运单号 | 耗时 ms |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: |",
    ])
    for row in rows:
        lines.append(
            f"| {row['dataset']} | {row['image']} | {mark(row['preprocess'])} | "
            f"{row['angle']} | {row['ocr_count']} | {mark(row['name_ok'])} "
            f"`{short_text(row['raw_receiver_name'])}` | {mark(row['phone_ok'])} "
            f"`{short_text(row['raw_phone'])}` | {mark(row['address_ok'])} "
            f"`{short_text(row['raw_address'])}` | {mark(row['tracking_ok'])} "
            f"`{short_text(row['raw_tracking_number'])}` | {row['elapsed_ms']} |"
        )

    lines.extend([
        "",
        "## 4. 结论",
        "",
        "- clean 样本用于验证清晰面单下的真实 OCR 主流程。",
        "- augmented 样本用于观察噪声、亮度、压缩等扰动对字段提取的影响。",
        "- rotated_raw 与 rotated_preprocessed 使用同一批图片，便于对比开启校正前后的效果。",
        "- 若某项为 `N`，说明 OCR 文本或字段提取没有完全命中标签值，可作为后续优化样例。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["paddle", "auto", "mock"], default="paddle")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "docs" / "10_ocr_integration_and_robustness.md"),
    )
    args = parser.parse_args()

    os.environ["OCR_MODE"] = args.mode

    rows: list[dict[str, Any]] = []
    for dataset, label_file, enable_preprocess in DATASET_CONFIGS:
        labels = load_labels(label_file)[: args.count]
        for label in labels:
            rows.append(evaluate(label, dataset, enable_preprocess))

    report = render_report(rows, args.mode, args.count)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
