# OCR 接入与鲁棒性测试记录

本文档记录“同学 1：OCR 接入与鲁棒性测试方向”的完成内容，包括 PaddleOCR 环境安装、开源模型下载、后端接入方式、测试方法、鲁棒性结果和后续优化建议。

## 1. 任务目标

本方向的目标是将项目从 mock OCR 升级为可调用真实 OCR 模型的系统。

原始 base 版本中，`backend/ocr_service.py` 根据上传图片文件名匹配标签 JSON，模拟返回 OCR 文本和文本框。这种方式可以保证演示闭环稳定，但并不是真正从图片中识别文字。

本次任务完成后，系统支持：

- 使用 PaddleOCR 真实识别快递面单图片。
- 将 PaddleOCR 原始输出统一转换为项目内部 OCR 格式。
- 继续保留 mock OCR 作为兜底方案。
- 通过环境变量在 `mock`、`paddle`、`auto` 三种模式间切换。
- 对 clean、augmented、rotated 三类样本进行鲁棒性测试。
- 输出测试报告，供后续 PPT 和答辩使用。

## 2. 环境与依赖

项目文档建议使用 Python 3.10 或 Python 3.11，避免 PaddleOCR 和 PaddlePaddle 在过新 Python 版本下出现兼容问题。

本次实际使用：

```text
Python 3.11.15
PaddlePaddle 3.2.0
PaddleOCR 3.7.0
CPU 推理
```

已在项目目录中创建独立虚拟环境：

```text
.venv/
```

基础依赖安装：

```powershell
uv pip install --python "C:\Users\34566\Desktop\生产实习\scsx\.venv\Scripts\python.exe" -r requirements.txt
```

PaddlePaddle CPU 版安装：

```powershell
uv pip install --python "C:\Users\34566\Desktop\生产实习\scsx\.venv\Scripts\python.exe" paddlepaddle==3.2.0 --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/
```

OCR 扩展依赖安装：

```powershell
uv pip install --python "C:\Users\34566\Desktop\生产实习\scsx\.venv\Scripts\python.exe" -r requirements-ocr.txt
```

环境验证命令：

```powershell
.venv\Scripts\python -c "import paddle; import paddleocr; print(paddle.__version__); print(paddleocr.__version__)"
```

验证结果：

```text
Paddle 3.2.0
PaddleOCR 3.7.0
cuda False
```

## 3. OCR 模型选择与下载

本项目只需要通用 OCR 能力，用于识别快递面单上的中文、英文和数字。因此采用 PaddleOCR 3.7 默认的 PP-OCRv6 通用 OCR pipeline。

首次运行 PaddleOCR 时，模型会自动下载到本机缓存目录：

```text
C:/Users/34566/.paddlex/official_models/
```

本次已下载并缓存：

```text
PP-OCRv6_medium_det
PP-OCRv6_medium_rec
```

含义：

- `PP-OCRv6_medium_det`：文本检测模型，用来找出图片中文字区域。
- `PP-OCRv6_medium_rec`：文本识别模型，用来识别每个文字区域中的具体内容。

模型下载完成后，后续运行会直接使用本地缓存，不需要重复下载。

## 4. 后端接入方式

主要修改文件：

```text
backend/config.py
backend/ocr_service.py
backend/extractor.py
```

### 4.1 OCR 模式配置

`backend/config.py` 已支持从环境变量读取 OCR 模式：

```text
OCR_MODE=mock
OCR_MODE=paddle
OCR_MODE=auto
```

三种模式说明：

| 模式 | 说明 |
| --- | --- |
| `mock` | 使用原有标签模拟 OCR，适合兜底演示 |
| `paddle` | 强制使用 PaddleOCR 真实识别 |
| `auto` | 优先使用 PaddleOCR，失败后回退 mock |

如果不设置环境变量，默认仍是：

```text
OCR_MODE=mock
```

这样可以保证原有 base 演示流程不会被破坏。

### 4.2 PaddleOCR 输出转换

PaddleOCR 原始结果中包含：

```text
rec_texts
rec_scores
rec_polys
```

项目内部统一使用的 OCR 结构为：

```json
{
  "text": "收方：张三 13812345678",
  "confidence": 0.98,
  "box": [[10, 10], [200, 10], [200, 40], [10, 40]]
}
```

因此在 `backend/ocr_service.py` 中新增了转换逻辑，将 PaddleOCR 结果转换为项目统一格式。

统一格式的好处是：

- 后续字段提取不需要关心 OCR 来源。
- 图片脱敏可以继续使用 OCR box。
- mock 和 PaddleOCR 可以自由切换。

### 4.3 保留 mock OCR 兜底

本次没有删除原有 mock OCR。

保留原因：

- PaddleOCR 首次运行需要下载模型。
- CPU 推理速度较慢。
- 答辩现场环境可能不稳定。
- mock OCR 可以保证项目完整链路随时可演示。

建议答辩时说明：

```text
系统支持真实 OCR，同时保留 mock OCR 作为容错演示模式。
```

## 5. 字段提取适配

真实 OCR 与 mock OCR 最大的区别是文本不一定规整。

mock OCR 中的文本通常是：

```text
收方地址：重庆市重庆市渝北区金开大道168号星光公寓6栋2100室
收方：吕俊峰 13687105423
运单号：81793571802948
```

真实 PaddleOCR 可能识别为：

```text
重庆市重庆市渝北区金开大道168号星光公寓6栋2100室
收方：吕俊峰 13687105423
81793571802948
订单号
07593059
```

因此本次对 `backend/extractor.py` 做了两项适配。

### 5.1 地址兜底提取

当 OCR 文本中没有“收方地址”标签时，系统会查找收方行之前最像地址的文本行。

判断依据包括：

- 文本长度足够。
- 包含省、市、区、县等区域词。
- 包含路、街、道、号、栋、室、小区、公寓等详细地址词。
- 排除寄方、原寄地、网址等无关内容。

### 5.2 运单号提取优化

真实 OCR 中可能同时出现：

```text
81793571802948
订单号
07593059
```

之前的规则容易把“订单号”后的短数字误认为快递单号。

本次优化后：

- 明确“运单号/快递单号”优先。
- 不再把普通“订单号”当作快递单号优先项。
- 没有明确标签时，优先选择最长的非手机号数字串。

## 6. 运行方式

### 6.1 使用 mock OCR

默认就是 mock 模式，不需要额外设置：

```powershell
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6.2 使用真实 PaddleOCR

PowerShell 中设置：

```powershell
$env:OCR_MODE="paddle"
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6.3 自动回退模式

```powershell
$env:OCR_MODE="auto"
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

auto 模式会优先尝试 PaddleOCR。如果真实 OCR 失败，则回退到 mock OCR。

## 7. 单张样本验证

使用真实 PaddleOCR 调用后端识别接口，clean 样本 `waybill_clean_0001.png` 可识别出：

```text
收件人：吕俊峰
手机号：13687105423
地址：重庆市重庆市渝北区金开大道168号星光公寓6栋2100室
运单号：81793571802948
```

接口返回后，字段会继续进入结构化脱敏：

```text
吕俊峰 -> 吕*峰
13687105423 -> 136****5423
重庆市重庆市渝北区金开大道168号星光公寓6栋2100室 -> 重庆市重庆市渝北区**
81793571802948 -> 8179******2948
```

## 8. 鲁棒性测试脚本

新增脚本：

```text
scripts/evaluate_ocr_robustness.py
```

运行命令：

```powershell
.venv\Scripts\python scripts\evaluate_ocr_robustness.py --mode paddle --count 5
```

测试内容：

- 5 张 clean 样本。
- 5 张 augmented 样本。
- 5 张 rotated 原图样本。
- 5 张 rotated 开启预处理后的样本。

总计 20 次真实 OCR 推理。

脚本会自动比较识别结果和标签中的标准答案，检查四项字段：

```text
收件人
手机号
地址
运单号
```

## 9. 鲁棒性测试结果

测试环境：

```text
OCR 模式：paddle
OCR 模型：PaddleOCR 3.7 默认 PP-OCRv6 通用 OCR pipeline
PaddlePaddle：CPU 推理
每组样本数：5
```

汇总结果：

| 数据集 | 样本数 | 姓名 | 手机号 | 地址 | 运单号 | 四项全对 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| clean | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| augmented | 5 | 5/5 | 3/5 | 5/5 | 5/5 | 3/5 |
| rotated_raw | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| rotated_preprocessed | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

结论：

- clean 样本识别效果较好，5 张全部四项字段识别正确。
- augmented 样本中姓名、地址、运单号稳定，手机号有 2 张受扰动影响识别错误。
- rotated 原图样本在当前轻微旋转范围内也能稳定识别。
- rotated 开启预处理后依然保持 5/5 全对。

## 10. 明细结果

| 数据集 | 图片 | 预处理 | 角度 | OCR 条数 | 姓名 | 手机号 | 地址 | 运单号 | 耗时 ms |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: |
| clean | waybill_clean_0001.png | N | 0.0 | 51 | Y `吕俊峰` | Y `13687105423` | Y `重庆市重庆市渝北区金开大道168号星...` | Y `81793571802948` | 37357 |
| clean | waybill_clean_0002.png | N | 0.0 | 51 | Y `施洋` | Y `13640442929` | Y `新疆维吾尔自治区乌鲁木齐市天山区解放...` | Y `1412654699108` | 34162 |
| clean | waybill_clean_0003.png | N | 0.0 | 51 | Y `孔明` | Y `13047885750` | Y `重庆市重庆市渝北区金开大道170号星...` | Y `06939218786354` | 32713 |
| clean | waybill_clean_0004.png | N | 0.0 | 52 | Y `何泽林` | Y `18875727943` | Y `湖南省株洲市天元区泰山路61号湘水湾...` | Y `62734054814893` | 33367 |
| clean | waybill_clean_0005.png | N | 0.0 | 52 | Y `魏若曦` | Y `13925287314` | Y `江苏省无锡市滨湖区太湖大道108号湖...` | Y `934254504794682` | 34141 |
| augmented | waybill_aug_0001.png | N | 0.0 | 52 | Y `吕俊峰` | N `17935718029` | Y `重庆市重庆市渝北区金开大道168号星...` | Y `81793571802948` | 33457 |
| augmented | waybill_aug_0002.png | N | 0.0 | 52 | Y `施洋` | N `14126546991` | Y `新疆维吾尔自治区乌鲁木齐市天山区解放...` | Y `1412654699108` | 33382 |
| augmented | waybill_aug_0003.png | N | 0.0 | 51 | Y `孔明` | Y `13047885750` | Y `重庆市重庆市渝北区金开大道170号星...` | Y `06939218786354` | 32954 |
| augmented | waybill_aug_0004.png | N | 0.0 | 50 | Y `何泽林` | Y `18875727943` | Y `湖南省株洲市天元区泰山路61号湘水湾...` | Y `62734054814893` | 32993 |
| augmented | waybill_aug_0005.png | N | 0.0 | 51 | Y `魏若曦` | Y `13925287314` | Y `江苏省无锡市滨湖区太湖大道108号湖...` | Y `934254504794682` | 34733 |
| rotated_raw | waybill_rotated_0001.png | N | 0.0 | 51 | Y `吕俊峰` | Y `13687105423` | Y `重庆市重庆市渝北区金开大道168号星...` | Y `81793571802948` | 32379 |
| rotated_raw | waybill_rotated_0002.png | N | 0.0 | 50 | Y `施洋` | Y `13640442929` | Y `新疆维吾尔自治区乌鲁木齐市天山区解放...` | Y `1412654699108` | 33233 |
| rotated_raw | waybill_rotated_0003.png | N | 0.0 | 52 | Y `孔明` | Y `13047885750` | Y `重庆市重庆市渝北区金开大道170号星...` | Y `06939218786354` | 33271 |
| rotated_raw | waybill_rotated_0004.png | N | 0.0 | 51 | Y `何泽林` | Y `18875727943` | Y `湖南省株洲市天元区泰山路61号湘水湾...` | Y `62734054814893` | 32599 |
| rotated_raw | waybill_rotated_0005.png | N | 0.0 | 52 | Y `魏若曦` | Y `13925287314` | Y `江苏省无锡市滨湖区太湖大道108号湖...` | Y `934254504794682` | 33160 |
| rotated_preprocessed | waybill_rotated_0001.png | Y | -2.0 | 50 | Y `吕俊峰` | Y `13687105423` | Y `重庆市重庆市渝北区金开大道168号星...` | Y `81793571802948` | 34692 |
| rotated_preprocessed | waybill_rotated_0002.png | Y | -4.5 | 50 | Y `施洋` | Y `13640442929` | Y `新疆维吾尔自治区乌鲁木齐市天山区解放...` | Y `1412654699108` | 36070 |
| rotated_preprocessed | waybill_rotated_0003.png | Y | 2.5 | 50 | Y `孔明` | Y `13047885750` | Y `重庆市重庆市渝北区金开大道170号星...` | Y `06939218786354` | 35485 |
| rotated_preprocessed | waybill_rotated_0004.png | Y | 3.3 | 51 | Y `何泽林` | Y `18875727943` | Y `湖南省株洲市天元区泰山路61号湘水湾...` | Y `62734054814893` | 40709 |
| rotated_preprocessed | waybill_rotated_0005.png | Y | -2.3 | 51 | Y `魏若曦` | Y `13925287314` | Y `江苏省无锡市滨湖区太湖大道108号湖...` | Y `934254504794682` | 35567 |

## 11. 当前限制

### 11.1 CPU 推理较慢

本次使用 CPU 版 PaddlePaddle，单张图片推理大约需要 30 到 40 秒。

如果后续需要更流畅演示，可以考虑：

- 降低上传图片尺寸。
- 使用 GPU 版 PaddlePaddle。
- 在后端启动时预热模型。
- 演示时优先使用少量样本。

### 11.2 augmented 手机号仍有误识别

augmented 样本中有 2 张手机号识别错误，例如：

```text
期望：13687105423
识别：17935718029
```

这说明噪声、压缩或模糊会影响数字识别。后续可优化：

- 对手机号区域做更强的图像增强。
- 使用更合适的文本检测阈值。
- 结合手机号正则和上下文进行候选修正。
- 增加人工复核提示。

### 11.3 前端还未开放 OCR 模式切换

当前 OCR 模式通过后端环境变量控制，前端页面还没有提供切换入口。

如果需要演示真实 OCR，需要先在后端启动前设置：

```powershell
$env:OCR_MODE="paddle"
```

## 12. 答辩可用表述

可以这样介绍本方向：

```text
我们在 base 版本 mock OCR 的基础上接入了 PaddleOCR 真实识别能力。系统现在支持 mock、paddle 和 auto 三种 OCR 模式。真实 OCR 使用 PP-OCRv6 通用模型，可以识别中文、英文和数字，并返回文本框坐标。我们将 PaddleOCR 结果统一转换成项目内部格式，使字段提取和图片脱敏模块无需改动即可继续使用。
```

可以这样介绍鲁棒性测试：

```text
我们分别测试了 clean、augmented 和 rotated 三类样本。clean 样本 5 张全部识别正确；rotated 样本在原图和开启预处理后均能正确识别；augmented 样本中手机号受噪声影响出现 2 次误识别，说明后续可以针对数字区域做进一步增强和校验。
```

可以这样说明保留 mock 的原因：

```text
由于 PaddleOCR 首次运行需要下载模型，且 CPU 推理速度较慢，因此系统保留了 mock OCR 作为兜底演示方案。这样即使真实 OCR 环境临时不可用，也能保证系统完整流程可以展示。
```

## 13. 本次完成文件清单

代码文件：

```text
backend/config.py
backend/ocr_service.py
backend/extractor.py
```

测试文件：

```text
tests/test_extractor.py
```

新增脚本：

```text
scripts/evaluate_ocr_robustness.py
```

文档文件：

```text
docs/10_ocr_integration_and_robustness.md
docs/08_team_status_and_tasks.md
README.md
```

## 14. 验证命令

自动测试：

```powershell
.venv\Scripts\python -m pytest -q
```

结果：

```text
8 passed
```

鲁棒性测试：

```powershell
.venv\Scripts\python scripts\evaluate_ocr_robustness.py --mode paddle --count 5
```

结果已记录在本文档第 9 节和第 10 节。
