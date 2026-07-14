from backend.extractor import extract_fields


def test_extract_fields_and_mask_structured_values():
    ocr_results = [
        {
            "text": "运单号：SF1234567890123",
            "confidence": 0.99,
            "box": [[10, 10], [200, 10], [200, 40], [10, 40]],
        },
        {
            "text": "收方地址：福建省泉州市丰泽区测试路88号创新公寓3栋100室",
            "confidence": 0.98,
            "box": [[10, 50], [500, 50], [500, 80], [10, 80]],
        },
        {
            "text": "收方：张三 13812345678",
            "confidence": 0.98,
            "box": [[10, 90], [260, 90], [260, 120], [10, 120]],
        },
    ]

    fields = extract_fields(ocr_results)

    assert fields["raw_receiver_name"] == "张三"
    assert fields["receiver_name"] == "张*"
    assert fields["raw_phone"] == "13812345678"
    assert fields["phone"] == "138****5678"
    assert fields["raw_address"] == "福建省泉州市丰泽区测试路88号创新公寓3栋100室"
    assert fields["address"] == "福建省泉州市丰泽区**"
    assert fields["raw_tracking_number"] == "SF1234567890123"
    assert fields["tracking_number"] == "SF12*******0123"


def test_missing_fields_return_none():
    fields = extract_fields([{"text": "普通备注：请轻拿轻放", "confidence": 0.8, "box": None}])

    assert fields["raw_receiver_name"] is None
    assert fields["raw_phone"] is None
    assert fields["raw_address"] is None
    assert fields["raw_tracking_number"] is None
