import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_node_json(script: str) -> dict:
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    return json.loads(completed.stdout)


def test_frontend_has_task3_controls() -> None:
    html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    required_ids = [
        "enablePreprocess",
        "mainView",
        "ocrView",
        "maskedView",
        "viewOcrBtn",
        "viewMaskedBtn",
        "backFromOcrBtn",
        "backFromMaskedBtn",
        "copyResultBtn",
        "downloadMaskedBtn",
        "exportJsonBtn",
        "clearBtn",
        "preprocessPanel",
        "preprocessStatus",
        "preprocessAngle",
        "preprocessedPreview",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in html


def test_frontend_exports_result_helpers() -> None:
    script = r"""
const helpers = require("./frontend/app.js");
const result = {
  receiver_name: "Zhang San",
  phone: "138****5678",
  raw_phone: "13812345678",
  address: "Fujian Quanzhou test road 88",
  tracking_number: "81793571802948",
  processing_time_ms: 18,
  masked_image_url: "/outputs/masked_demo.png",
  preprocessed_image_url: "/outputs/preprocessed_demo.png",
  preprocess: {
    enabled: true,
    applied: true,
    angle: -2.6,
    message: "corrected"
  },
  ocr_texts: [
    { text: "receiver Zhang San 13812345678", confidence: 0.98, box: null }
  ]
};

process.stdout.write(JSON.stringify({
  imageUrl: helpers.buildApiUrl(result.masked_image_url),
  preprocess: helpers.describePreprocess(result.preprocess),
  exportPayload: helpers.buildResultExport(result)
}));
"""

    data = run_node_json(script)

    assert data["imageUrl"] == "http://127.0.0.1:8000/outputs/masked_demo.png"
    assert data["preprocess"]["visible"] is True
    assert data["preprocess"]["status"] == "\u5df2\u542f\u7528\uff0c\u5df2\u6821\u6b63"
    assert data["preprocess"]["angle"] == "-2.6\u00b0"
    assert data["exportPayload"]["receiver_name"] == "Zhang San"
    assert data["exportPayload"]["phone"] == "138****5678"
    assert "raw_phone" not in data["exportPayload"]
    assert data["exportPayload"]["preprocess"]["applied"] is True


def test_frontend_resolves_hash_views() -> None:
    script = r"""
const helpers = require("./frontend/app.js");
process.stdout.write(JSON.stringify({
  main: helpers.resolveViewFromHash(""),
  ocr: helpers.resolveViewFromHash("#ocr"),
  masked: helpers.resolveViewFromHash("#masked"),
  unknown: helpers.resolveViewFromHash("#else")
}));
"""

    data = run_node_json(script)

    assert data == {
        "main": "main",
        "ocr": "ocr",
        "masked": "masked",
        "unknown": "main",
    }


def test_frontend_appends_preprocess_form_field() -> None:
    app_js = (PROJECT_ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'formData.append("enable_preprocess"' in app_js


def test_frontend_removes_button_motion_styles() -> None:
    html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (PROJECT_ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert "motion-btn" not in html
    assert "motion-btn" not in css
    assert "@keyframes button-pop" not in css
