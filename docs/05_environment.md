# 环境配置与依赖说明

## 1. 推荐 Python 环境

建议使用独立虚拟环境，Python 版本推荐：

```text
Python 3.10 或 Python 3.11
```

不建议一开始使用过新的 Python 版本，避免 PaddleOCR、PaddlePaddle 或部分图像库出现兼容问题。

Windows + Anaconda 示例：

```bash
conda create -n waybill_ocr python=3.10 -y
conda activate waybill_ocr
python -m pip install --upgrade pip
```

普通 venv 示例：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
```

## 2. MVP 基础依赖

MVP 阶段先安装：

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` 用于：

- FastAPI 后端接口。
- 文件上传。
- 图片读取、绘制和脱敏。
- 虚拟快递面单生成。
- 基础测试。

核心依赖：

| 依赖 | 用途 |
| --- | --- |
| fastapi | 后端 Web 框架 |
| uvicorn | 本地开发服务器 |
| python-multipart | 支持表单文件上传 |
| pillow | 生成面单、读取图片、绘制遮挡框 |
| numpy | 图像处理和后续 OCR 数据转换 |
| faker | 生成虚拟姓名、手机号、地址等数据 |
| pytest | 后续写测试 |
| httpx | FastAPI 测试客户端相关依赖 |

## 3. OCR 扩展依赖

等 MVP 闭环跑通后，再安装 OCR 扩展：

```bash
python -m pip install -r requirements-ocr.txt
```

`requirements-ocr.txt` 用于：

- PaddleOCR 真实文字识别。
- OpenCV 图像预处理增强。

## 4. PaddleOCR 与模型选择

本项目只需要“通用 OCR”，不需要训练模型，也不需要文档解析大模型。

推荐使用：

```text
PP-OCRv6 通用 OCR pipeline
```

原因：

- 能识别中文、英文和数字，适合快递面单。
- 能返回文本和文本框，方便后续图片打码。
- 官方文档中 PP-OCRv6 是 PaddleOCR 3.7 默认的通用 OCR 模型系列。

不建议本项目使用：

```text
PaddleOCR-VL
PP-StructureV3
PP-ChatOCRv4
```

这些更适合复杂文档解析、版面分析或大模型信息抽取。快递面单项目用它们会显得重，而且环境更麻烦。

## 5. PaddlePaddle 推理引擎

PaddleOCR 需要推理引擎。官方文档建议使用默认的 `paddle_static` 引擎时，先安装 PaddlePaddle。

### 5.1 CPU 版

如果不追求速度，CPU 版最稳：

```bash
python -m pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

然后安装 OCR 扩展：

```bash
python -m pip install -r requirements-ocr.txt
```

### 5.2 GPU 版

如果要用 NVIDIA GPU，需要根据显卡驱动选择版本。

CUDA 11.8 对应：

```bash
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
```

CUDA 12.6 对应：

```bash
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
```

如果只是大作业演示，优先 CPU 版，少折腾。

## 6. 环境验证

基础环境验证：

```bash
python -c "import fastapi, PIL, faker; print('base env ok')"
```

PaddleOCR 验证：

```bash
python -c "import paddleocr; print('PaddleOCR', paddleocr.__version__)"
```

PaddlePaddle 验证：

```bash
python -c "import paddle; print('Paddle', paddle.__version__); print('cuda', paddle.is_compiled_with_cuda())"
```

## 7. 后续代码中预计导入的包

### 7.1 后端接口

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
```

### 7.2 文件与路径处理

```python
from pathlib import Path
from uuid import uuid4
import shutil
import time
```

### 7.3 图片处理

```python
from PIL import Image, ImageDraw, ImageFont
import numpy as np
```

### 7.4 字段提取

```python
import re
```

### 7.5 虚拟数据生成

```python
from faker import Faker
import random
import json
```

### 7.6 PaddleOCR

具体 API 可能随 PaddleOCR 版本变化，后续实现时以实际安装版本为准。目标是统一转换为项目内部格式：

```python
[
    {
        "text": "电话：13812345678",
        "confidence": 0.97,
        "box": [[50, 125], [310, 125], [310, 160], [50, 160]]
    }
]
```

## 8. 开发建议

建议开发顺序：

```text
先装 requirements.txt
  -> 完成后端接口和前端闭环
  -> 完成虚拟面单生成
  -> 再装 PaddlePaddle + requirements-ocr.txt
  -> 接入真实 PaddleOCR
```

这样即使 OCR 环境安装失败，也不会影响系统主体演示。
