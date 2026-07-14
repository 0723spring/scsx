# Base 版本运行说明

## 1. 当前 base 版本包含什么

当前版本已经跑通基础闭环：

```text
前端选择图片
  -> 原图预览
  -> 调用后端 /api/recognize
  -> mock OCR 返回文本和框坐标
  -> 字段提取
  -> 图片脱敏
  -> 前端展示结构化字段、OCR 文本和脱敏图片
```

说明：

- 现在的 OCR 是 mock OCR，不是真实 PaddleOCR。
- 如果上传的是 `dataset/generated/clean/` 或 `dataset/generated/augmented/` 中生成的数据，后端会按文件名从标签 JSON 中读取真值和 box，模拟 OCR 输出。
- 后续接 PaddleOCR 时，主要替换 `backend/ocr_service.py` 的 `run_ocr()` 实现即可。

## 2. 启动后端

在项目根目录运行：

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 3. 打开前端

可以直接打开：

```text
frontend/index.html
```

也可以用 VS Code Live Server 或任意静态服务器打开。

前端默认请求：

```text
http://127.0.0.1:8000/api/recognize
```

## 4. 推荐测试图片

推荐选择：

```text
dataset/generated/clean/waybill_clean_0001.png
dataset/generated/augmented/waybill_aug_0001.png
```

上传这些图片时，mock OCR 可以根据文件名匹配标签，返回对应字段。

轻微旋转图片位于：

```text
dataset/generated/rotated/waybill_rotated_0001.png
```

当前 base 版本可以上传 rotated 图片，但由于旋转样本的 box 未重新计算，图片脱敏定位不作为最终效果评估。后续如果实现 `backend/preprocess.py` 图像校正模块，再用 rotated 数据测试校正前后的 OCR 和字段提取效果。

额外独立测试图片位于：

```text
dataset/test/waybill_extra_test_0001.png
```

注意：`dataset/test/` 不加入当前 mock OCR 标签索引。也就是说，如果后端仍然只使用 mock OCR，上传这些图片不会得到对应真值结果；它们主要用于后续验证真实 OCR 或模型泛化识别能力。

## 5. 已实现接口

### GET /api/health

返回服务状态。

### POST /api/recognize

参数：

```text
file: 图片文件
```

返回：

- 收件人姓名
- 脱敏手机号
- 原始手机号
- 收件地址
- 快递单号
- OCR 文本列表
- 脱敏图片地址
- 处理耗时

## 6. 后续可以分给队友的改进点

- 将 `backend/ocr_service.py` 中的 mock OCR 替换为 PaddleOCR。
- 优化 `backend/extractor.py` 中字段提取规则。
- 优化 `backend/masker.py` 中图片脱敏效果，例如改为马赛克。
- 优化前端页面样式和交互。
- 增加下载脱敏图片、导出 JSON、批量识别等功能。
