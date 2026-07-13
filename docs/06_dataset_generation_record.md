# 数据生成记录

## 1. 数据集概况

本次生成虚拟顺丰快递面单主数据集共 `300` 张，另生成轻微旋转鲁棒性测试集 `60` 张。

主数据集包括：

- 干净样本：`210` 张
- 增强样本：`90` 张
- 训练集：`210` 张
- 验证集：`45` 张
- 测试集：`45` 张

旋转鲁棒性测试集：

- rotated：`60` 张
- 不混入 train/val/test
- 用于测试后端图像校正和 OCR 对轻微倾斜图片的适应能力

本项目不训练 OCR 模型，训练集主要用于开发和调试字段提取、OCR 接入、隐私脱敏等规则；验证集用于调整参数后检查效果；测试集用于最终统计和答辩展示。

## 2. 生成工具

数据由 Python 脚本生成：

```text
scripts/generate_waybills.py
```

主要使用：

- Pillow：打开模板、绘制中文文字、保存图片、进行亮度/对比度/模糊/JPEG 压缩处理。
- NumPy：添加轻微高斯噪声。
- Python 标准库：随机生成字段、保存 JSON 标签、划分数据集。

模板文件：

```text
dataset/templates/sf_blank_template.jpg
```

坐标配置文件：

```text
dataset/templates/template_config.json
```

所有姓名、手机号、地址、订单号、快递单号均为脚本合成的虚拟数据，不包含真实个人隐私。

## 3. 输出位置

干净图片：

```text
dataset/generated/clean/
```

增强图片：

```text
dataset/generated/augmented/
```

旋转测试图片：

```text
dataset/generated/rotated/
```

标签文件：

```text
dataset/labels/labels_clean.json
dataset/labels/labels_augmented.json
dataset/labels/labels_rotated.json
dataset/labels/train.json
dataset/labels/val.json
dataset/labels/test.json
dataset/labels/robustness_test.json
```

图片路径均以 `dataset/` 为相对根目录记录，例如：

```text
generated/clean/waybill_clean_0001.png
generated/augmented/waybill_aug_0001.png
generated/rotated/waybill_rotated_0001.png
```

## 4. 数据划分

采用固定数量划分：

| 集合 | 干净样本 | 增强样本 | 合计 |
| --- | ---: | ---: | ---: |
| train | 150 | 60 | 210 |
| val | 30 | 15 | 45 |
| test | 30 | 15 | 45 |

总计：

| 类型 | 数量 |
| --- | ---: |
| clean | 210 |
| augmented | 90 |
| rotated | 60 |
| main all | 300 |
| total with rotated | 360 |

生成随机种子：

```text
20260713
```

## 5. 增强处理

增强样本只使用不改变图像几何位置的处理，因此标签中的主联字段框坐标仍然有效。

增强处理包括：

- 亮度轻微变化：约 `0.88` 到 `1.12`
- 对比度轻微变化：约 `0.90` 到 `1.10`
- 少量高斯噪声：sigma 约 `2.0` 到 `6.0`
- 轻微高斯模糊：部分样本使用，半径约 `0.25` 到 `0.65`
- JPEG 压缩模拟：质量约 `65` 到 `88`

主增强集中未使用的增强：

- 不旋转
- 不透视变换
- 不裁剪
- 不翻转
- 不做强遮挡

这样可以模拟真实拍摄、压缩和轻微噪声场景，同时避免重新计算 box 坐标。

## 6. 旋转鲁棒性测试集

旋转测试集由 clean 样本派生，输出到：

```text
dataset/generated/rotated/
```

标签输出到：

```text
dataset/labels/labels_rotated.json
dataset/labels/robustness_test.json
```

旋转规则：

- 数量：`60` 张
- 角度范围：约 `-5°` 到 `5°`
- 不做透视变换
- 不做裁剪配置
- 画布大小保持不变
- 空白区域使用白色填充

重要说明：

- 旋转后没有重新计算文字框坐标。
- 因此旋转样本的 `metadata.boxes_valid` 为 `false`。
- 字段真值仍然有效，可以用于 OCR 识别和字段提取测试。
- 该数据集主要用于后续图像预处理模块，例如自动倾斜校正。

## 7. 标签说明

每条标签包含：

- `image`：图片相对路径
- `fields`：字段真值，包括收件人、手机号、地址、运单号等
- `main_boxes`：主联关键字段框，格式为 `[x1, y1, x2, y2]`
- `metadata`：生成标记、增强参数、box 是否有效

增强样本的 `metadata.boxes_valid` 为 `true`，因为增强过程未改变文字几何位置。

旋转样本的 `metadata.boxes_valid` 为 `false`，因为旋转会改变文字框位置，而当前项目没有重新计算旋转后的 box。
