"""图片隐私脱敏文件。

文件职责：
1. 提供 mask_phone(phone) 字符串脱敏函数。
2. 提供 mask_sensitive_info(image_path, ocr_results, fields) 图片脱敏函数。
3. 使用 Pillow 打开上传图片。
4. 根据 OCR 文本和 box 判断敏感区域。
5. 第一版使用黑色矩形遮挡敏感区域。
6. 增强版可实现马赛克脱敏。
7. 将脱敏图片保存到 backend/outputs/。
8. 返回可被前端访问的 masked_image_url。
"""

from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw

from .config import OUTPUT_DIR
from .file_utils import output_url


def mask_phone(phone: str | None) -> str | None:
    if not phone or len(phone) != 11:
        return phone
    return phone[:3] + "****" + phone[-4:]


def quad_to_rect(box: list[list[int]] | None, padding: int = 6) -> list[int] | None:
    if not box:
        return None
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    return [min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding]


def is_sensitive_text(text: str, fields: dict) -> bool:
    sensitive_values = [
        fields.get("receiver_name"),
        fields.get("raw_phone"),
        fields.get("address"),
        fields.get("tracking_number"),
    ]
    if any(value and value in text for value in sensitive_values):
        return True
    return any(keyword in text for keyword in ["收方", "收件人", "收方地址", "运单号"])


def mask_sensitive_info(image_path: str | Path, ocr_results: list[dict], fields: dict) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    for item in ocr_results:
        text = str(item.get("text", ""))
        if not is_sensitive_text(text, fields):
            continue
        rect = quad_to_rect(item.get("box"))
        if not rect:
            continue
        draw.rectangle(rect, fill="black")

    output_path = OUTPUT_DIR / f"masked_{uuid4().hex[:12]}.png"
    image.save(output_path)
    return output_url(output_path)
