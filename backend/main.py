"""FastAPI 后端入口文件。

文件职责：
1. 创建 FastAPI app 实例。
2. 配置 CORS，允许本地前端访问后端接口。
3. 挂载 outputs 静态目录，用于访问脱敏后的图片。
4. 实现 GET /api/health 健康检查接口。
5. 实现 POST /api/recognize 图片识别接口。
6. 在识别接口中调用 file_utils 保存上传图片。
7. 在识别接口中调用 services.recognize_waybill 串联 OCR、字段提取和图片脱敏。
8. 统一返回 schemas.py 中约定的响应结构。
9. 捕获常见异常并返回 success=false 的 JSON。
"""

import time

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS, OUTPUT_DIR, SERVICE_NAME
from .file_utils import UploadValidationError, ensure_runtime_dirs, save_upload_file
from .schemas import error_response, success_response
from .services import recognize_waybill


ensure_runtime_dirs()

app = FastAPI(title="Express Waybill OCR", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/api/health")
def health() -> dict:
    return success_response(
        "service is running",
        {
            "service": SERVICE_NAME,
            "status": "ok",
        },
    )


@app.post("/api/recognize")
async def recognize(
    file: UploadFile = File(...),
    enable_preprocess: bool = Form(False),
) -> JSONResponse:
    started_at = time.perf_counter()
    try:
        image_path, original_filename = await save_upload_file(file)
        result = recognize_waybill(
            image_path,
            original_filename=original_filename,
            enable_preprocess=enable_preprocess,
        )
        fields = result["fields"]
        message = "识别成功"
        if any(fields.get(key) is None for key in ["receiver_name", "raw_phone", "address", "tracking_number"]):
            message = "识别完成，部分字段未识别"

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        data = {
            **fields,
            "ocr_texts": result["ocr_results"],
            "masked_image_url": result["masked_image_url"],
            "preprocessed_image_url": result["preprocessed_image_url"],
            "preprocess": result["preprocess"],
            "processing_time_ms": elapsed_ms,
        }
        return JSONResponse(success_response(message, data))
    except UploadValidationError as exc:
        return JSONResponse(error_response(str(exc)), status_code=400)
    except Exception as exc:
        return JSONResponse(error_response(f"识别失败：{exc}"), status_code=500)
