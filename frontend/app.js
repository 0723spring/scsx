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
12. 支持任务三演示增强：图像校正参数、复制、下载、清空、导出 JSON。
*/

(function initWaybillFrontend(global) {
  const API_BASE = "http://127.0.0.1:8000";

  function buildApiUrl(path) {
    if (!path) {
      return "";
    }
    if (/^https?:\/\//i.test(path)) {
      return path;
    }
    return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  }

  function resolveViewFromHash(hash) {
    const view = String(hash || "").replace(/^#/, "").toLowerCase();
    if (view === "ocr" || view === "masked") {
      return view;
    }
    return "main";
  }

  function describePreprocess(preprocess) {
    if (!preprocess) {
      return {
        visible: false,
        status: "未返回",
        angle: "-",
        message: "后端未返回图像校正信息",
      };
    }

    const enabled = Boolean(preprocess.enabled);
    const applied = Boolean(preprocess.applied);
    const angle = typeof preprocess.angle === "number" && Number.isFinite(preprocess.angle)
      ? `${Number(preprocess.angle).toFixed(1).replace(/\.0$/, "")}°`
      : "-";

    let status = "未启用";
    if (enabled && applied) {
      status = "已启用，已校正";
    } else if (enabled) {
      status = "已启用，未校正";
    }

    return {
      visible: true,
      status,
      angle,
      message: preprocess.message || status,
    };
  }

  function normalizeOcrTexts(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    return items.map((item) => ({
      text: item && item.text ? String(item.text) : "",
      confidence: typeof item?.confidence === "number" ? item.confidence : null,
      box: item?.box || null,
    }));
  }

  function buildResultExport(data) {
    const preprocess = data?.preprocess
      ? {
          enabled: Boolean(data.preprocess.enabled),
          applied: Boolean(data.preprocess.applied),
          angle: typeof data.preprocess.angle === "number" ? data.preprocess.angle : null,
          message: data.preprocess.message || null,
        }
      : null;

    return {
      receiver_name: data?.receiver_name || null,
      phone: data?.phone || null,
      address: data?.address || null,
      tracking_number: data?.tracking_number || null,
      processing_time_ms: typeof data?.processing_time_ms === "number" ? data.processing_time_ms : null,
      masked_image_url: data?.masked_image_url ? buildApiUrl(data.masked_image_url) : null,
      preprocessed_image_url: data?.preprocessed_image_url ? buildApiUrl(data.preprocessed_image_url) : null,
      preprocess,
      ocr_texts: normalizeOcrTexts(data?.ocr_texts),
    };
  }

  function buildCopyText(data) {
    const payload = buildResultExport(data);
    const lines = [
      `收件人：${payload.receiver_name || "-"}`,
      `手机号：${payload.phone || "-"}`,
      `快递单号：${payload.tracking_number || "-"}`,
      `地址：${payload.address || "-"}`,
      `耗时：${payload.processing_time_ms ?? "-"} ms`,
    ];

    if (payload.preprocess) {
      const preprocess = describePreprocess(payload.preprocess);
      lines.push(`图像校正：${preprocess.status}`);
      lines.push(`旋转角度：${preprocess.angle}`);
    }

    if (payload.ocr_texts.length) {
      lines.push("");
      lines.push("OCR 文本：");
      payload.ocr_texts.forEach((item, index) => {
        lines.push(`${index + 1}. ${item.text}`);
      });
    }

    return lines.join("\n");
  }

  function createTimestamp() {
    const now = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return [
      now.getFullYear(),
      pad(now.getMonth() + 1),
      pad(now.getDate()),
      "_",
      pad(now.getHours()),
      pad(now.getMinutes()),
      pad(now.getSeconds()),
    ].join("");
  }

  function downloadBlob(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function triggerUrlDownload(url, filename) {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.target = "_blank";
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }

  const exported = {
    API_BASE,
    buildApiUrl,
    resolveViewFromHash,
    describePreprocess,
    buildResultExport,
    buildCopyText,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = exported;
  }

  if (!global.document) {
    return;
  }

  const fileInput = document.querySelector("#fileInput");
  const enablePreprocess = document.querySelector("#enablePreprocess");
  const recognizeBtn = document.querySelector("#recognizeBtn");
  const viewOcrBtn = document.querySelector("#viewOcrBtn");
  const viewMaskedBtn = document.querySelector("#viewMaskedBtn");
  const copyResultBtn = document.querySelector("#copyResultBtn");
  const downloadMaskedBtn = document.querySelector("#downloadMaskedBtn");
  const exportJsonBtn = document.querySelector("#exportJsonBtn");
  const clearBtn = document.querySelector("#clearBtn");
  const backFromOcrBtn = document.querySelector("#backFromOcrBtn");
  const backFromMaskedBtn = document.querySelector("#backFromMaskedBtn");
  const serviceStatus = document.querySelector("#serviceStatus");
  const recognitionStatus = document.querySelector("#recognitionStatus");
  const mainView = document.querySelector("#mainView");
  const ocrView = document.querySelector("#ocrView");
  const maskedView = document.querySelector("#maskedView");
  const sourcePreview = document.querySelector("#sourcePreview");
  const maskedPreview = document.querySelector("#maskedPreview");
  const preprocessedPreview = document.querySelector("#preprocessedPreview");
  const sourceFrame = sourcePreview.closest(".preview-frame");
  const maskedFrame = maskedPreview.closest(".preview-frame");
  const preprocessedFrame = preprocessedPreview.closest(".preview-frame");
  const preprocessedPanel = document.querySelector("#preprocessedPanel");
  const preprocessPanel = document.querySelector("#preprocessPanel");
  const preprocessStatus = document.querySelector("#preprocessStatus");
  const preprocessAngle = document.querySelector("#preprocessAngle");
  const preprocessMessage = document.querySelector("#preprocessMessage");

  const fields = {
    receiverName: document.querySelector("#receiverName"),
    receiverPhone: document.querySelector("#receiverPhone"),
    trackingNumber: document.querySelector("#trackingNumber"),
    processingTime: document.querySelector("#processingTime"),
    receiverAddress: document.querySelector("#receiverAddress"),
  };
  const ocrList = document.querySelector("#ocrList");

  let selectedFile = null;
  let latestResult = null;

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

  function setActionButtonsEnabled() {
    const hasResult = Boolean(latestResult);
    viewOcrBtn.disabled = !hasResult;
    viewMaskedBtn.disabled = !latestResult?.masked_image_url;
    copyResultBtn.disabled = !hasResult;
    exportJsonBtn.disabled = !hasResult;
    downloadMaskedBtn.disabled = !latestResult?.masked_image_url;
    clearBtn.disabled = !selectedFile && !hasResult;
  }

  function setActiveView(viewName) {
    const view = resolveViewFromHash(viewName);
    mainView.classList.toggle("is-hidden", view !== "main");
    ocrView.classList.toggle("is-hidden", view !== "ocr");
    maskedView.classList.toggle("is-hidden", view !== "masked");
  }

  function navigateToView(viewName) {
    const view = resolveViewFromHash(viewName);
    const targetHash = view === "main" ? "#main" : `#${view}`;
    if (global.location.hash !== targetHash) {
      global.location.hash = targetHash;
      return;
    }
    setActiveView(targetHash);
  }

  function resetPreprocessResult() {
    preprocessPanel.classList.add("is-hidden");
    setText(preprocessStatus, "-");
    setText(preprocessAngle, "-");
    setText(preprocessMessage, "-");
    preprocessedPreview.removeAttribute("src");
    preprocessedFrame.classList.remove("has-image");
    preprocessedPanel.classList.add("is-hidden");
  }

  function resetResult() {
    latestResult = null;
    setText(fields.receiverName, "-");
    setText(fields.receiverPhone, "-");
    setText(fields.trackingNumber, "-");
    setText(fields.processingTime, "-");
    setText(fields.receiverAddress, "-");
    ocrList.innerHTML = "<li>暂无 OCR 文本</li>";
    maskedPreview.removeAttribute("src");
    maskedFrame.classList.remove("has-image");
    resetPreprocessResult();
    setActionButtonsEnabled();
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

  function renderPreprocess(data) {
    const shouldShowInfo = Boolean(data.preprocess || data.preprocessed_image_url);
    if (!shouldShowInfo) {
      resetPreprocessResult();
      return;
    }

    const description = describePreprocess(data.preprocess);
    preprocessPanel.classList.remove("is-hidden");
    setText(preprocessStatus, description.status);
    setText(preprocessAngle, description.angle);
    setText(preprocessMessage, description.message);

    if (data.preprocessed_image_url) {
      preprocessedPreview.src = buildApiUrl(data.preprocessed_image_url);
      preprocessedFrame.classList.add("has-image");
      preprocessedPanel.classList.remove("is-hidden");
    } else {
      preprocessedPreview.removeAttribute("src");
      preprocessedFrame.classList.remove("has-image");
      preprocessedPanel.classList.add("is-hidden");
    }
  }

  function renderResult(data) {
    latestResult = data;
    setText(fields.receiverName, data.receiver_name);
    setText(fields.receiverPhone, data.phone);
    setText(fields.trackingNumber, data.tracking_number);
    setText(fields.processingTime, `${data.processing_time_ms} ms`);
    setText(fields.receiverAddress, data.address);
    renderOcrTexts(data.ocr_texts);

    if (data.masked_image_url) {
      maskedPreview.src = buildApiUrl(data.masked_image_url);
      maskedFrame.classList.add("has-image");
    }

    renderPreprocess(data);
    setActionButtonsEnabled();
  }

  async function copyToClipboard(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  fileInput.addEventListener("change", () => {
    selectedFile = fileInput.files[0] || null;
    resetResult();

    if (!selectedFile) {
      recognizeBtn.disabled = true;
      sourcePreview.removeAttribute("src");
      sourceFrame.classList.remove("has-image");
      setStatus(recognitionStatus, "等待上传");
      setActionButtonsEnabled();
      return;
    }

    sourcePreview.src = URL.createObjectURL(selectedFile);
    sourceFrame.classList.add("has-image");
    recognizeBtn.disabled = false;
    setStatus(recognitionStatus, "已选择图片");
    setActionButtonsEnabled();
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
    formData.append("enable_preprocess", enablePreprocess.checked ? "true" : "false");

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

  copyResultBtn.addEventListener("click", async () => {
    if (!latestResult) {
      return;
    }

    try {
      await copyToClipboard(buildCopyText(latestResult));
      setStatus(recognitionStatus, "结果已复制", "ok");
    } catch (error) {
      setStatus(recognitionStatus, "复制失败", "error");
    }
  });

  downloadMaskedBtn.addEventListener("click", () => {
    if (!latestResult?.masked_image_url) {
      return;
    }
    triggerUrlDownload(buildApiUrl(latestResult.masked_image_url), `masked_waybill_${createTimestamp()}.png`);
  });

  exportJsonBtn.addEventListener("click", () => {
    if (!latestResult) {
      return;
    }
    const content = JSON.stringify(buildResultExport(latestResult), null, 2);
    downloadBlob(`waybill_result_${createTimestamp()}.json`, content, "application/json;charset=utf-8");
  });

  clearBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    recognizeBtn.disabled = true;
    sourcePreview.removeAttribute("src");
    sourceFrame.classList.remove("has-image");
    resetResult();
    setStatus(recognitionStatus, "等待上传");
    navigateToView("main");
  });

  viewOcrBtn.addEventListener("click", () => {
    navigateToView("ocr");
  });

  viewMaskedBtn.addEventListener("click", () => {
    navigateToView("masked");
  });

  backFromOcrBtn.addEventListener("click", () => {
    navigateToView("main");
  });

  backFromMaskedBtn.addEventListener("click", () => {
    navigateToView("main");
  });

  global.addEventListener("hashchange", () => {
    setActiveView(global.location.hash);
  });

  setActiveView(global.location.hash);
  checkHealth();
})(typeof window !== "undefined" ? window : globalThis);
