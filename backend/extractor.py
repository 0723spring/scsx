"""字段提取文件。

文件职责：
1. 接收 OCR 结果列表。
2. 合并 OCR 文本，形成便于正则匹配的完整文本。
3. 抽取收件人姓名 receiver_name。
4. 抽取原始手机号 raw_phone。
5. 调用脱敏规则生成 phone，例如 13812345678 -> 138****5678。
6. 抽取地址 address。
7. 抽取快递单号 tracking_number。
8. 字段未识别时返回 None，不让整个识别流程失败。
9. 后续可增加不同模板和不同快递公司的规则兜底。
"""

import re

from .masker import mask_phone


PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
TRACKING_PATTERN = re.compile(r"(?:运单号|快递单号|单号)[:：]?\s*([A-Z]{0,4}\d{10,18})")
RECEIVER_PATTERN = re.compile(r"(?:收方|收件人)[:：]\s*([\u4e00-\u9fa5]{2,4})")
ADDRESS_PATTERN = re.compile(r"(?:收方地址|地址)[:：]\s*(.+)")


def normalize_texts(ocr_results: list[dict]) -> list[str]:
    return [str(item.get("text", "")).strip() for item in ocr_results if item.get("text")]


def extract_tracking_number(text: str) -> str | None:
    match = TRACKING_PATTERN.search(text)
    if match:
        return match.group(1)
    fallback = re.search(r"\b\d{12,18}\b", text)
    return fallback.group(0) if fallback else None


def extract_receiver_name(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        if ("收方" in line or "收件人" in line) and "地址" not in line and PHONE_PATTERN.search(line):
            match = RECEIVER_PATTERN.search(line)
            if match:
                return match.group(1)
    match = RECEIVER_PATTERN.search(full_text)
    return match.group(1) if match else None


def extract_receiver_address(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        if "收方地址" in line or line.startswith("地址"):
            match = ADDRESS_PATTERN.search(line)
            if match:
                return match.group(1).strip()
    match = ADDRESS_PATTERN.search(full_text)
    return match.group(1).strip() if match else None


def extract_fields(ocr_results: list[dict]) -> dict:
    lines = normalize_texts(ocr_results)
    full_text = "\n".join(lines)
    raw_phone = None

    for line in lines:
        if "收方" in line or "收件人" in line:
            match = PHONE_PATTERN.search(line)
            if match:
                raw_phone = match.group(0)
                break
    if not raw_phone:
        match = PHONE_PATTERN.search(full_text)
        raw_phone = match.group(0) if match else None

    return {
        "receiver_name": extract_receiver_name(lines, full_text),
        "phone": mask_phone(raw_phone) if raw_phone else None,
        "raw_phone": raw_phone,
        "address": extract_receiver_address(lines, full_text),
        "tracking_number": extract_tracking_number(full_text),
    }
