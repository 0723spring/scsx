"""业务流程编排文件。

文件职责：
1. 提供 recognize_waybill(image_path) 主流程函数。
2. 调用 ocr_service.run_ocr 获取 OCR 结果。
3. 调用 extractor.extract_fields 从 OCR 文本中抽取结构化字段。
4. 调用 masker.mask_sensitive_info 生成脱敏图片。
5. 汇总字段、OCR 结果、脱敏图片路径，返回给 main.py。
6. 本文件只负责流程串联，不直接写 OCR、正则或图片处理细节。
"""

from pathlib import Path

from .extractor import extract_fields
from .masker import mask_sensitive_info
from .ocr_service import run_ocr
from .preprocess import preprocess_image


def recognize_waybill(
    image_path: str | Path,
    original_filename: str | None = None,
    enable_preprocess: bool = False,
) -> dict:
    preprocess_result = preprocess_image(image_path, enable_preprocess=enable_preprocess)
    ocr_image_path = preprocess_result["image_path"]

    ocr_results = run_ocr(ocr_image_path, original_filename=original_filename)
    fields = extract_fields(ocr_results)
    masked_image_url = mask_sensitive_info(ocr_image_path, ocr_results, fields)

    return {
        "fields": fields,
        "ocr_results": ocr_results,
        "masked_image_url": masked_image_url,
        "preprocessed_image_url": preprocess_result["preprocessed_image_url"],
        "preprocess": preprocess_result["preprocess"],
    }
