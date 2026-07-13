# 基于 OCR 的快递面单信息识别与隐私保护系统

本项目面向生产实习大作业，目标是在本地实现一个完整可演示的快递面单处理系统：

1. 生成虚拟快递面单数据。
2. 上传快递面单图片。
3. 进行 OCR 文字识别。
4. 抽取收件人、手机号、地址、快递单号等关键字段。
5. 对敏感信息进行结构化脱敏和图片区域打码。
6. 在前端页面展示原图、识别结果、OCR 原文和脱敏图片。

项目优先保证“闭环可运行”，再逐步替换真实 OCR、增强字段提取和优化隐私打码效果。

## 技术路线

- 后端：FastAPI
- 前端：原生 HTML + CSS + JavaScript
- OCR：前期 mock OCR，后期接入 PaddleOCR
- 图片处理：Pillow，必要时补充 OpenCV
- 数据存储：本地文件 + JSON，不引入数据库
- 运行方式：本地前后端分离

## 文档目录

- [项目整体设计](docs/01_project_design.md)
- [后端接口定义](docs/02_api_spec.md)
- [虚拟数据、OCR 与脱敏方案](docs/03_data_generation_and_ocr.md)
- [开发流程与验收标准](docs/04_development_process.md)

## 推荐项目结构

```text
express_waybill_ocr/
├── backend/
│   ├── main.py
│   ├── schemas.py
│   ├── services.py
│   ├── ocr_service.py
│   ├── extractor.py
│   ├── masker.py
│   ├── file_utils.py
│   ├── uploads/
│   └── outputs/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── dataset/
│   ├── templates/
│   ├── generated/
│   └── labels/
├── docs/
├── scripts/
│   └── generate_waybills.py
├── requirements.txt
└── README.md
```

## 当前版本优先级

第一优先级是 MVP 闭环：

- 图片上传
- 原图预览
- 后端识别接口
- 结构化字段展示
- OCR 文本展示
- 脱敏图片生成与展示

第二优先级是增强项：

- PaddleOCR 真实接入
- 正则字段提取优化
- 基于 OCR box 的图片区域打码
- 批量生成虚拟快递面单
- 导出 JSON 或下载脱敏图片
