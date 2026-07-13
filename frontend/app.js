/*
前端交互逻辑文件。

文件职责：
1. 获取文件选择 input、预览图、按钮、结果区域等 DOM 元素。
2. 监听图片选择事件。
3. 使用 URL.createObjectURL 显示原图预览。
4. 控制“开始识别”按钮状态。
5. 点击按钮后构造 FormData。
6. 调用 http://127.0.0.1:8000/api/recognize。
7. 展示 loading 状态。
8. 根据后端返回的 JSON 渲染结构化字段。
9. 渲染 OCR 完整文本列表。
10. 拼接 masked_image_url 并展示脱敏图片。
11. 处理网络错误和后端 success=false 的错误提示。
*/

const API_BASE = "http://127.0.0.1:8000";

const fileInput = document.querySelector("#fileInput");
const recognizeBtn = document.querySelector("#recognizeBtn");
const serviceStatus = document.querySelector("#serviceStatus");
const recognitionStatus = document.querySelector("#recognitionStatus");
const sourcePreview = document.querySelector("#sourcePreview");
const maskedPreview = document.querySelector("#maskedPreview");
const sourceFrame = sourcePreview.closest(".preview-frame");
const maskedFrame = maskedPreview.closest(".preview-frame");

const fields = {
  receiverName: document.querySelector("#receiverName"),
  receiverPhone: document.querySelector("#receiverPhone"),
  trackingNumber: document.querySelector("#trackingNumber"),
  processingTime: document.querySelector("#processingTime"),
  receiverAddress: document.querySelector("#receiverAddress"),
};
const ocrList = document.querySelector("#ocrList");

let selectedFile = null;

function setStatus(element, text, type = "") {
  element.textContent = text;
  element.classList.remove("ok", "error");
  if (type) {
    element.classList.add(type);
  }
}

function setText(element, value) {
  element.textContent = value || "-";
}

function resetResult() {
  setText(fields.receiverName, "-");
  setText(fields.receiverPhone, "-");
  setText(fields.trackingNumber, "-");
  setText(fields.processingTime, "-");
  setText(fields.receiverAddress, "-");
  ocrList.innerHTML = "<li>暂无 OCR 文本</li>";
  maskedPreview.removeAttribute("src");
  maskedFrame.classList.remove("has-image");
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    const result = await response.json();
    if (result.success) {
      setStatus(serviceStatus, "服务正常", "ok");
      return;
    }
    throw new Error(result.message || "服务异常");
  } catch (error) {
    setStatus(serviceStatus, "服务未连接", "error");
  }
}

function renderOcrTexts(items) {
  if (!items || items.length === 0) {
    ocrList.innerHTML = "<li>未识别到 OCR 文本</li>";
    return;
  }

  ocrList.innerHTML = "";
  for (const item of items) {
    const li = document.createElement("li");
    const confidence = typeof item.confidence === "number"
      ? ` (${Math.round(item.confidence * 100)}%)`
      : "";
    li.textContent = `${item.text}${confidence}`;
    ocrList.appendChild(li);
  }
}

function renderResult(data) {
  setText(fields.receiverName, data.receiver_name);
  setText(fields.receiverPhone, data.phone);
  setText(fields.trackingNumber, data.tracking_number);
  setText(fields.processingTime, `${data.processing_time_ms} ms`);
  setText(fields.receiverAddress, data.address);
  renderOcrTexts(data.ocr_texts);

  if (data.masked_image_url) {
    maskedPreview.src = `${API_BASE}${data.masked_image_url}`;
    maskedFrame.classList.add("has-image");
  }
}

fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files[0] || null;
  resetResult();

  if (!selectedFile) {
    recognizeBtn.disabled = true;
    sourcePreview.removeAttribute("src");
    sourceFrame.classList.remove("has-image");
    setStatus(recognitionStatus, "等待上传");
    return;
  }

  sourcePreview.src = URL.createObjectURL(selectedFile);
  sourceFrame.classList.add("has-image");
  recognizeBtn.disabled = false;
  setStatus(recognitionStatus, "已选择图片");
});

recognizeBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus(recognitionStatus, "请先选择图片", "error");
    return;
  }

  recognizeBtn.disabled = true;
  setStatus(recognitionStatus, "识别中...");

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch(`${API_BASE}/api/recognize`, {
      method: "POST",
      body: formData,
    });
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.message || "识别失败");
    }

    renderResult(result.data);
    setStatus(recognitionStatus, result.message, "ok");
  } catch (error) {
    setStatus(recognitionStatus, error.message || "识别失败", "error");
  } finally {
    recognizeBtn.disabled = false;
  }
});

checkHealth();
