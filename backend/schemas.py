"""接口响应结构定义文件。

文件职责：
1. 定义统一 API 响应结构：success、message、data。
2. 定义 OCR 文本项结构：text、confidence、box。
3. 定义快递面单识别结果结构。
4. 提供成功响应和失败响应的辅助构造函数。
5. 保证后端所有接口返回格式一致，方便前端联调。
"""

from typing import Any


def success_response(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data or {},
    }


def error_response(message: str, data: Any = None) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": data,
    }
