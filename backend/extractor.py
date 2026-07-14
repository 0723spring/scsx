"""Rule-based field extraction from normalized OCR results."""

from __future__ import annotations

import re

from .masker import mask_address, mask_name, mask_phone, mask_tracking_number


PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
TRACKING_PATTERN = re.compile(
    r"(?:\u8fd0\u5355\u53f7|\u5feb\u9012\u5355\u53f7)"
    r"[:\uff1a]?\s*([A-Z]{0,4}\d{10,18})",
    re.IGNORECASE,
)
TRACKING_FALLBACK_PATTERN = re.compile(r"\b(?:[A-Z]{2,4})?\d{10,18}\b", re.IGNORECASE)
RECEIVER_PATTERN = re.compile(
    r"(?:\u6536\u65b9|\u6536\u4ef6\u4eba|\u6536\u8d27\u4eba|\u6536\u4ef6|\u59d3\u540d)"
    r"[:\uff1a\s]*([\u4e00-\u9fff\u00b7]{2,8})"
)
ADDRESS_PATTERN = re.compile(
    r"(?:\u6536\u65b9\u5730\u5740|\u6536\u4ef6\u5730\u5740|\u6536\u8d27\u5730\u5740|\u5730\u5740)"
    r"[:\uff1a\s]*(.+)"
)

RECEIVER_KEYWORDS = ("\u6536\u65b9", "\u6536\u4ef6\u4eba", "\u6536\u8d27\u4eba", "\u6536\u4ef6")
ADDRESS_KEYWORDS = ("\u6536\u65b9\u5730\u5740", "\u6536\u4ef6\u5730\u5740", "\u6536\u8d27\u5730\u5740", "\u5730\u5740")
ADDRESS_HINTS = ("\u7701", "\u5e02", "\u533a", "\u53bf", "\u8def", "\u8857", "\u9053", "\u53f7", "\u680b", "\u5ba4", "\u5c0f\u533a", "\u516c\u5bd3")


def normalize_texts(ocr_results: list[dict]) -> list[str]:
    return [
        re.sub(r"\s+", " ", str(item.get("text", "")).strip())
        for item in ocr_results
        if item.get("text")
    ]


def _after_colon(text: str) -> str:
    parts = re.split(r"[:\uff1a]", text, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else text.strip()


def extract_tracking_number(text: str) -> str | None:
    match = TRACKING_PATTERN.search(text)
    if match:
        return match.group(1).upper()

    candidates = []
    for match in TRACKING_FALLBACK_PATTERN.finditer(text):
        value = match.group(0).upper()
        if not PHONE_PATTERN.fullmatch(value):
            candidates.append(value)
    if not candidates:
        return None
    return max(candidates, key=lambda value: (len(re.sub(r"\D", "", value)), len(value)))


def extract_receiver_name(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        if any(keyword in line for keyword in RECEIVER_KEYWORDS) and "\u5730\u5740" not in line:
            candidate = PHONE_PATTERN.sub("", _after_colon(line)).strip()
            match = re.search(r"[\u4e00-\u9fff\u00b7]{2,8}", candidate)
            if match:
                return match.group(0)

    match = RECEIVER_PATTERN.search(full_text)
    return match.group(1) if match else None


def extract_receiver_address(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        if any(keyword in line for keyword in ADDRESS_KEYWORDS) and "\u5bc4\u65b9" not in line:
            match = ADDRESS_PATTERN.search(line)
            if match:
                return match.group(1).strip()

    match = ADDRESS_PATTERN.search(full_text)
    if match:
        return match.group(1).strip()

    candidates = [
        (index, line)
        for index, line in enumerate(lines)
        if is_likely_address_line(line)
    ]
    if not candidates:
        return None

    receiver_indexes = [
        index
        for index, line in enumerate(lines)
        if any(keyword in line for keyword in RECEIVER_KEYWORDS) and "\u5730\u5740" not in line
    ]
    if receiver_indexes:
        receiver_index = receiver_indexes[0]
        before_receiver = [item for item in candidates if item[0] < receiver_index]
        if before_receiver:
            return before_receiver[-1][1]

    return candidates[0][1]


def is_likely_address_line(line: str) -> bool:
    if len(line) < 10:
        return False
    if any(skip in line for skip in ("\u5bc4\u65b9", "\u539f\u5bc4\u5730", "EXPRESS", "http", "qiao")):
        return False
    hint_count = sum(1 for hint in ADDRESS_HINTS if hint in line)
    has_region = any(region in line for region in ("\u7701", "\u5e02", "\u533a", "\u53bf"))
    has_detail = any(detail in line for detail in ("\u8def", "\u8857", "\u9053", "\u53f7", "\u680b", "\u5ba4", "\u5c0f\u533a", "\u516c\u5bd3"))
    return hint_count >= 3 and has_region and has_detail


def extract_phone(lines: list[str], full_text: str) -> str | None:
    for line in lines:
        if any(keyword in line for keyword in RECEIVER_KEYWORDS) and "\u5730\u5740" not in line:
            match = PHONE_PATTERN.search(line)
            if match:
                return match.group(0)

    match = PHONE_PATTERN.search(full_text)
    return match.group(0) if match else None


def extract_fields(ocr_results: list[dict]) -> dict:
    lines = normalize_texts(ocr_results)
    full_text = "\n".join(lines)

    raw_name = extract_receiver_name(lines, full_text)
    raw_phone = extract_phone(lines, full_text)
    raw_address = extract_receiver_address(lines, full_text)
    raw_tracking_number = extract_tracking_number(full_text)

    return {
        "receiver_name": mask_name(raw_name),
        "raw_receiver_name": raw_name,
        "phone": mask_phone(raw_phone),
        "raw_phone": raw_phone,
        "address": mask_address(raw_address),
        "raw_address": raw_address,
        "tracking_number": mask_tracking_number(raw_tracking_number),
        "raw_tracking_number": raw_tracking_number,
    }
