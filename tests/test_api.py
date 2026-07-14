from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from backend.main import app


client = TestClient(app)


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 80), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"


def test_recognize_endpoint_accepts_preprocess_flag():
    response = client.post(
        "/api/recognize",
        data={"enable_preprocess": "true"},
        files={"file": ("waybill_clean_0001.png", _image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "preprocess" in data
    assert data["preprocess"]["enabled"] is True
    assert data["phone"] == "136****5423"
    assert data["raw_phone"] == "13687105423"
    assert data["masked_image_url"].startswith("/outputs/masked_")
