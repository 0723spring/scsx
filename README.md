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
- [环境配置与依赖说明](docs/05_environment.md)
- [Base 版本运行说明](docs/07_base_app_usage.md)
- [当前进度与团队任务分工草案](docs/08_team_status_and_tasks.md)
- [OCR 接入与鲁棒性测试记录](docs/10_ocr_integration_and_robustness.md)

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

## 虚拟快递面单生成（已经做好了）

模板图片放置位置：

```text
dataset/templates/sf_blank_template.jpg
```

坐标配置文件：

```text
dataset/templates/template_config.json
```

生成预览调试图：

```bash
python scripts/generate_waybills.py --preview
```

预览图输出到：

```text
dataset/generated/template_preview.png
```

生成 20 张模拟面单：

```bash
python scripts/generate_waybills.py --count 20
```

生成正式 300 张数据集，包含 clean、augmented、train、val、test：

```bash
python scripts/generate_waybills.py --make-dataset --seed 20260713
```

生成 60 张轻微旋转鲁棒性测试集：

```bash
python scripts/generate_waybills.py --make-rotated --rotated-count 60 --seed 20260713
```

生成 10 张独立额外测试图，专门用于检查是否真的使用 OCR/模型泛化识别：

```bash
python scripts/generate_waybills.py --make-extra-test --extra-test-count 10 --seed 20260714
```

图片输出目录：

```text
dataset/generated/
```

标签文件：

```text
dataset/labels/labels.json
```

说明：

- 所有姓名、电话、地址均为虚拟合成数据。
- 模板中的 Logo、服务热线和条形码保持不变。
- 本项目不做条形码解析，只对图片中文字进行 OCR 识别。
- 如果中文字体加载失败，可以使用 `--font-path` 指定本机中文字体，例如 `C:/Windows/Fonts/msyh.ttc`。
- 正式数据集生成记录见 [数据生成记录](docs/06_dataset_generation_record.md)。
- `rotated/` 数据只用于图像校正和 OCR 鲁棒性测试，不混入主 train/val/test。
- `dataset/test/` 是额外独立测试集，不加入 mock OCR 标签索引；如果仍使用 mock OCR，上传这些图片不会得到对应真值识别结果。

## 方向 2 增强说明

图像预处理、字段提取与脱敏方向的实现说明见：

- [方向 2：图像预处理、字段提取与脱敏说明](docs/09_direction2_preprocess_extraction_masking.md)
