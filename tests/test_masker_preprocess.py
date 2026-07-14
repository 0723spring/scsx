from pathlib import Path

from PIL import Image, ImageDraw

from backend.masker import mask_sensitive_info
from backend.preprocess import preprocess_image


def test_mask_sensitive_info_creates_mosaic_output(tmp_path):
    image_path = tmp_path / "sample.png"
    image = Image.new("RGB", (240, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 30, 220, 70], fill="black")
    image.save(image_path)

    url = mask_sensitive_info(
        image_path,
        [
            {
                "text": "收方：张三 13812345678",
                "confidence": 0.98,
                "box": [[20, 30], [220, 30], [220, 70], [20, 70]],
            }
        ],
        {"raw_receiver_name": "张三", "raw_phone": "13812345678"},
    )

    assert url.startswith("/outputs/masked_")
    assert Path("backend", "outputs", url.removeprefix("/outputs/")).exists()


def test_preprocess_disabled_keeps_original_path(tmp_path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (100, 60), "white").save(image_path)

    result = preprocess_image(image_path, enable_preprocess=False)

    assert result["image_path"] == image_path
    assert result["preprocessed_image_url"] is None
    assert result["preprocess"]["enabled"] is False
    assert result["preprocess"]["applied"] is False
