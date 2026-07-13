"""文件处理工具文件。

文件职责：
1. 校验上传文件是否存在。
2. 校验图片后缀是否为 jpg、jpeg、png、bmp 等支持格式。
3. 校验图片大小是否超过限制。
4. 使用 Pillow 验证图片是否可以正常打开。
5. 为上传文件生成唯一文件名，避免覆盖。
6. 保存上传图片到 backend/uploads/。
7. 为脱敏图片生成输出路径和访问 URL。
8. 处理 Windows 路径和 URL 路径之间的转换。
"""

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image

from .config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, OUTPUT_DIR, UPLOAD_DIR


class UploadValidationError(ValueError):
    pass


def ensure_runtime_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UploadValidationError("不支持的图片格式")
    return suffix


async def save_upload_file(file: UploadFile) -> tuple[Path, str]:
    if not file or not file.filename:
        raise UploadValidationError("未上传图片文件")

    suffix = validate_extension(file.filename)
    content = await file.read()
    if not content:
        raise UploadValidationError("上传图片为空")
    if len(content) > MAX_UPLOAD_SIZE:
        raise UploadValidationError("图片大小超过限制")

    ensure_runtime_dirs()
    safe_name = f"{Path(file.filename).stem}_{uuid4().hex[:8]}{suffix}"
    save_path = UPLOAD_DIR / safe_name
    save_path.write_bytes(content)

    try:
        with Image.open(save_path) as image:
            image.verify()
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        raise UploadValidationError("图片无法读取，请检查文件是否损坏") from exc

    return save_path, file.filename


def output_url(path: Path) -> str:
    return f"/outputs/{path.name}"
