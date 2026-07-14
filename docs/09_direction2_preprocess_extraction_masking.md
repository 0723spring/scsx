# 方向 2：图像预处理、字段提取与脱敏说明

## 1. 已实现内容

本方向已在后端完成以下增强：

- 新增 `backend/preprocess.py`，提供 `preprocess_image(image_path, enable_preprocess=False)`。
- `POST /api/recognize` 新增表单参数 `enable_preprocess`，用于控制是否启用图像校正。
- `backend/services.py` 接入处理链路：上传图片 -> 可选预处理 -> OCR -> 字段提取 -> 图片脱敏。
- `backend/extractor.py` 增强字段提取规则，支持收方姓名、手机号、地址、运单号。
- `backend/masker.py` 增强结构化字段脱敏，并将图片黑块遮挡改为马赛克。
- `backend/ocr_service.py` 支持读取 rotated 标签；当 `boxes_valid=false` 时不直接复用旧框做精确脱敏。
- 新增测试覆盖字段提取、结构化脱敏、图片脱敏、预处理关闭状态。

## 2. 图像预处理流程

预处理入口：

```python
preprocess_image(image_path, enable_preprocess=False)
```

当 `enable_preprocess=false` 时，直接返回原图路径。

当 `enable_preprocess=true` 时，流程为：

```text
读取图片
  -> 灰度化
  -> 深色像素阈值分割
  -> 在 -8° 到 8° 范围内搜索水平投影最优角度
  -> 如果倾斜角度超过阈值，则旋转校正
  -> 输出校正后的图片到 backend/outputs/
```

返回结构示例：

```json
{
  "preprocessed_image_url": "/outputs/preprocessed_xxx.png",
  "preprocess": {
    "enabled": true,
    "applied": true,
    "angle": -2.0,
    "message": "deskew correction applied"
  }
}
```

说明：当前实现没有强依赖 OpenCV，基础环境只需 Pillow 和 NumPy 即可运行，便于演示和部署。

## 3. 字段提取规则

OCR 结果统一为：

```json
{
  "text": "收方：张三 13812345678",
  "confidence": 0.98,
  "box": [[10, 10], [200, 10], [200, 40], [10, 40]]
}
```

字段提取采用规则法：

- 手机号：匹配 `1[3-9]\d{9}`。
- 运单号：优先匹配 `运单号/快递单号/单号` 后的编号，兜底匹配 10 到 18 位数字或字母数字组合。
- 收件人：优先从包含 `收方/收件人/收货人` 的行提取，避免把地址行识别为姓名。
- 地址：优先从 `收方地址/收件地址/收货地址/地址` 行提取。

结构化结果同时保留原始值和脱敏值：

```json
{
  "receiver_name": "张*",
  "raw_receiver_name": "张三",
  "phone": "138****5678",
  "raw_phone": "13812345678",
  "address": "福建省泉州市丰泽区**",
  "raw_address": "福建省泉州市丰泽区测试路88号创新公寓3栋100室",
  "tracking_number": "SF12*******0123",
  "raw_tracking_number": "SF1234567890123"
}
```

## 4. 脱敏策略

结构化字段脱敏：

- 姓名：保留首尾，隐藏中间；两字姓名保留姓氏。
- 手机号：保留前三位和后四位。
- 地址：保留省市区县等大致区域，隐藏详细门牌、小区、楼栋和房间号。
- 运单号：保留前四位和后四位。

图片脱敏：

- 根据 OCR 文本和字段值判断敏感文本行。
- 将 OCR box 转为矩形区域。
- 对敏感区域做马赛克处理。
- 如果 rotated 标签中 `boxes_valid=false`，不直接使用旧 box 做图片脱敏，避免框位偏移导致误判。

## 5. 已验证样例

已通过以下验证：

- 6 个自动化测试全部通过。
- clean 样本 `waybill_clean_0001.png` 能提取姓名、手机号、地址、运单号，并生成马赛克脱敏图。
- rotated 样本 `waybill_rotated_0001.png` 在开启预处理后生成校正图，返回角度信息，例如 `angle=-2.0`。
- 脱敏前后对比图：`docs/screenshots/direction2_mask_compare.png`。
- 旋转校正前后对比图：`docs/screenshots/direction2_preprocess_compare.png`。

运行测试命令：

```bash
python -m pytest -q
```

本机验证时使用 Python 3.14：

```bash
C:\Users\Dell\AppData\Local\Programs\Python\Python314\python.exe -m pytest -q
```

## 6. 可继续增加的功能点

如果还想把方向 2 做得更充实，可以继续加：

- 字符级脱敏：手机号只马赛克中间四位，而不是整行 OCR box。
- OCR 置信度标记：低置信度字段在前端标黄，方便人工复核。
- 脱敏强度选项：轻度脱敏、标准脱敏、严格脱敏三档。
- 批量评估脚本：一次性跑 10 张 clean、10 张 augmented、3 张 rotated，并输出准确率表格。
- 图片前后对比导出：自动保存原图、校正图、脱敏图到 `docs/screenshots/`。
- 字段规则配置化：把关键词和正则放入 JSON，方便后续适配不同快递模板。
