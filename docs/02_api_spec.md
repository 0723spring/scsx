# 后端接口定义

## 1. 基础信息

后端框架：FastAPI

开发环境基础地址：

```text
http://127.0.0.1:8000
```

前端开发地址可以使用：

```text
http://127.0.0.1:5500
```

后端需要开启 CORS，至少允许：

```text
http://127.0.0.1:5500
http://localhost:5500
```

开发阶段也可以临时允许所有来源。

## 2. 统一响应格式

所有业务接口统一返回以下结构：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

失败时：

```json
{
  "success": false,
  "message": "错误原因",
  "data": null
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| success | boolean | 是 | 请求是否成功 |
| message | string | 是 | 结果说明或错误原因 |
| data | object/null | 是 | 成功时为数据对象，失败时为 null |

## 3. 健康检查接口

### 3.1 请求

```text
GET /api/health
```

### 3.2 成功响应

```json
{
  "success": true,
  "message": "service is running",
  "data": {
    "service": "express-waybill-ocr",
    "status": "ok"
  }
}
```

### 3.3 用途

- 检查后端是否启动。
- 前端联调时确认接口可访问。
- 答辩演示时说明系统服务状态。

## 4. 快递面单识别接口

### 4.1 请求

```text
POST /api/recognize
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | File | 是 | 用户上传的快递面单图片 |

支持格式：

```text
.jpg
.jpeg
.png
.bmp
```

建议限制：

- 单张图片不超过 10 MB。
- 文件必须能被 Pillow 正常打开。

### 4.2 成功响应

```json
{
  "success": true,
  "message": "识别成功",
  "data": {
    "receiver_name": "张三",
    "phone": "138****5678",
    "raw_phone": "13812345678",
    "address": "福建省泉州市丰泽区测试路88号",
    "tracking_number": "SF1234567890123",
    "ocr_texts": [
      {
        "text": "收件人：张三",
        "confidence": 0.98,
        "box": [[50, 80], [220, 80], [220, 115], [50, 115]]
      },
      {
        "text": "电话：13812345678",
        "confidence": 0.97,
        "box": [[50, 125], [310, 125], [310, 160], [50, 160]]
      }
    ],
    "masked_image_url": "/outputs/masked_20260713_001.jpg",
    "processing_time_ms": 320
  }
}
```

### 4.3 data 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| receiver_name | string/null | 收件人姓名 |
| phone | string/null | 脱敏后的手机号，用于前端展示 |
| raw_phone | string/null | 原始手机号，系统内部使用，前端默认不突出展示 |
| address | string/null | 收件地址 |
| tracking_number | string/null | 快递单号 |
| ocr_texts | array | OCR 识别文本列表 |
| masked_image_url | string/null | 脱敏图片访问地址 |
| processing_time_ms | number | 后端处理耗时，单位毫秒 |

### 4.4 ocr_texts 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| text | string | OCR 识别出的文本 |
| confidence | number | 置信度，范围建议为 0 到 1 |
| box | array/null | 文本框坐标，格式为四个点 |

`box` 格式：

```json
[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
```

如果处于 mock OCR 阶段，可以返回固定 box。如果暂时没有 box，也可以返回 null，但图片打码能力会受影响。

## 5. 部分字段未识别

如果 OCR 成功，但部分字段未提取出来，不应该直接返回失败。

示例：

```json
{
  "success": true,
  "message": "识别完成，部分字段未识别",
  "data": {
    "receiver_name": "张三",
    "phone": null,
    "raw_phone": null,
    "address": "福建省泉州市丰泽区测试路88号",
    "tracking_number": null,
    "ocr_texts": [
      {
        "text": "收件人：张三",
        "confidence": 0.95,
        "box": [[50, 80], [220, 80], [220, 115], [50, 115]]
      }
    ],
    "masked_image_url": "/outputs/masked_20260713_002.jpg",
    "processing_time_ms": 280
  }
}
```

## 6. 常见失败响应

### 6.1 未上传文件

```json
{
  "success": false,
  "message": "未上传图片文件",
  "data": null
}
```

### 6.2 文件格式不支持

```json
{
  "success": false,
  "message": "不支持的图片格式",
  "data": null
}
```

### 6.3 图片过大

```json
{
  "success": false,
  "message": "图片大小超过限制",
  "data": null
}
```

### 6.4 图片损坏

```json
{
  "success": false,
  "message": "图片无法读取，请检查文件是否损坏",
  "data": null
}
```

### 6.5 OCR 异常

```json
{
  "success": false,
  "message": "OCR 识别失败",
  "data": null
}
```

## 7. 脱敏图片访问

后端将 `outputs/` 目录挂载为静态目录。

访问方式：

```text
GET /outputs/{filename}
```

示例：

```text
GET /outputs/masked_20260713_001.jpg
```

前端从 `/api/recognize` 返回的 `masked_image_url` 获取地址后，直接设置到 `img.src`。

如果前后端分离运行，前端需要拼接后端基础地址：

```javascript
const imageUrl = `http://127.0.0.1:8000${data.masked_image_url}`;
```

## 8. 前端调用示例

```javascript
const formData = new FormData();
formData.append("file", selectedFile);

const response = await fetch("http://127.0.0.1:8000/api/recognize", {
  method: "POST",
  body: formData
});

const result = await response.json();

if (!result.success) {
  throw new Error(result.message);
}

    renderRecognitionResult(result.data);
```

## 10. 图像预处理参数补充

`POST /api/recognize` 支持可选表单参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| enable_preprocess | boolean | 否 | 是否启用图像倾斜校正，默认 `false` |

请求示例：

```javascript
const formData = new FormData();
formData.append("file", selectedFile);
formData.append("enable_preprocess", "true");
```

返回结果中新增：

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

字段结果中同时包含脱敏值和原始值，例如 `phone/raw_phone`、`address/raw_address`、`tracking_number/raw_tracking_number`。前端展示时建议优先展示脱敏值。

## 9. 后端处理伪代码

```python
@app.post("/api/recognize")
async def recognize(file: UploadFile = File(...)):
    start_time = time.time()

    image_path = save_upload_file(file)
    result = recognize_waybill(image_path)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "success": True,
        "message": "识别成功",
        "data": {
            "receiver_name": result["fields"]["receiver_name"],
            "phone": result["fields"]["phone"],
            "raw_phone": result["fields"]["raw_phone"],
            "address": result["fields"]["address"],
            "tracking_number": result["fields"]["tracking_number"],
            "ocr_texts": result["ocr_results"],
            "masked_image_url": result["masked_image_url"],
            "processing_time_ms": elapsed_ms
        }
    }
```
