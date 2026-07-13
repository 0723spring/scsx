"""后端配置文件。

文件职责：
1. 配置项目基础目录。
2. 配置 uploads 和 outputs 目录。
3. 配置允许上传的图片格式。
4. 配置最大上传文件大小。
5. 配置 OCR_MODE，可选 mock 或 paddle。
6. 配置 CORS 允许的前端地址。
7. 后续如有需要，可从环境变量读取配置。
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / "backend"
UPLOAD_DIR = BACKEND_DIR / "uploads"
OUTPUT_DIR = BACKEND_DIR / "outputs"
DATASET_DIR = BASE_DIR / "dataset"
LABEL_DIR = DATASET_DIR / "labels"

SERVICE_NAME = "express-waybill-ocr"
OCR_MODE = "mock"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

CORS_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "null",
]
