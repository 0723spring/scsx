"""虚拟快递面单生成脚本。

文件职责：
1. 读取 dataset/templates/ 下的快递面单模板图片。
2. 随机生成虚拟收件人姓名。
3. 随机生成虚拟手机号。
4. 随机生成虚拟地址。
5. 随机生成快递单号。
6. 使用 Pillow 将字段绘制到模板固定位置。
7. 保存生成图片到 dataset/generated/。
8. 保存对应标签 JSON 到 dataset/labels/。
9. 标签 JSON 中记录字段文本和 box 坐标。
10. 支持通过命令行参数指定生成数量、模板路径和输出目录。
11. 支持正式数据集生成、轻量图像增强和 train/val/test 划分。

The script keeps the original template unchanged. It only writes virtual
waybill text onto configured blank areas, then saves generated images and a
labels.json file.
"""

from __future__ import annotations

import argparse
import io
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = PROJECT_ROOT / "dataset" / "templates" / "sf_blank_template.jpg"
DEFAULT_CONFIG = PROJECT_ROOT / "dataset" / "templates" / "template_config.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "dataset" / "generated"
DEFAULT_LABELS_PATH = PROJECT_ROOT / "dataset" / "labels" / "labels.json"
DEFAULT_DATASET_RECORD = PROJECT_ROOT / "docs" / "06_dataset_generation_record.md"


SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN_NAMES = [
    "伟",
    "芳",
    "娜",
    "敏",
    "静",
    "强",
    "磊",
    "洋",
    "勇",
    "艳",
    "杰",
    "娟",
    "涛",
    "明",
    "超",
    "秀英",
    "文静",
    "志强",
    "子涵",
    "雨欣",
    "建国",
    "建华",
    "国强",
    "国庆",
    "海燕",
    "海涛",
    "晓明",
    "晓红",
    "晓峰",
    "丽丽",
    "丽华",
    "桂英",
    "桂芳",
    "玉兰",
    "玉梅",
    "春梅",
    "春华",
    "秋菊",
    "冬梅",
    "秀兰",
    "秀珍",
    "淑芬",
    "淑华",
    "俊杰",
    "俊峰",
    "俊豪",
    "家豪",
    "家辉",
    "佳怡",
    "佳琪",
    "佳欣",
    "欣怡",
    "欣然",
    "梦瑶",
    "梦婷",
    "思雨",
    "思琪",
    "宇航",
    "宇轩",
    "浩然",
    "浩宇",
    "博文",
    "博涛",
    "泽宇",
    "泽林",
    "晨曦",
    "晨阳",
    "一鸣",
    "一凡",
    "梓涵",
    "梓轩",
    "若曦",
    "若琳",
    "诗涵",
    "诗雨",
    "嘉怡",
    "嘉豪",
    "子墨",
    "子轩",
    "雨桐",
    "雨泽",
    "依娜",
    "依婷",
    "雪梅",
    "雪晴",
    "兰英",
    "兰芳",
    "志远",
    "志鹏",
    "鹏飞",
    "立新",
    "立军",
    "红梅",
    "红霞",
    "小龙",
    "小雨",
    "小慧",
    "小敏",
]

ADDRESS_PARTS = [
    ("湖北省", "孝感市", "孝南区", "北京路", "测试小区"),
    ("福建省", "泉州市", "丰泽区", "东海大街", "海景花园"),
    ("广东省", "深圳市", "南山区", "科技园路", "创新公寓"),
    ("北京市", "北京市", "朝阳区", "望京东路", "测试大厦"),
    ("陕西省", "西安市", "长安区", "学府大道", "书香苑"),
    ("浙江省", "杭州市", "西湖区", "文三路", "云栖小区"),
    ("四川省", "成都市", "武侯区", "天府三街", "锦城花园"),
    ("江苏省", "南京市", "鼓楼区", "中山北路", "梧桐里"),
    ("上海市", "上海市", "浦东新区", "张江路", "科创家园"),
    ("上海市", "上海市", "徐汇区", "漕溪北路", "文苑小区"),
    ("天津市", "天津市", "南开区", "卫津路", "学府花园"),
    ("重庆市", "重庆市", "渝北区", "金开大道", "星光公寓"),
    ("山东省", "济南市", "历下区", "经十路", "泉城花园"),
    ("山东省", "青岛市", "市南区", "香港中路", "海岸名苑"),
    ("河南省", "郑州市", "金水区", "文化路", "绿城小区"),
    ("湖南省", "长沙市", "岳麓区", "麓山南路", "湘江雅苑"),
    ("湖北省", "武汉市", "洪山区", "珞喻路", "光谷新苑"),
    ("安徽省", "合肥市", "蜀山区", "长江西路", "天鹅湖小区"),
    ("江西省", "南昌市", "红谷滩区", "丰和中大道", "江景花园"),
    ("河北省", "石家庄市", "裕华区", "槐安东路", "阳光新城"),
    ("山西省", "太原市", "小店区", "平阳路", "锦绣苑"),
    ("辽宁省", "沈阳市", "和平区", "青年大街", "万象公馆"),
    ("吉林省", "长春市", "朝阳区", "人民大街", "春城小区"),
    ("黑龙江省", "哈尔滨市", "南岗区", "学府路", "冰城家园"),
    ("广西壮族自治区", "南宁市", "青秀区", "民族大道", "绿地中央"),
    ("云南省", "昆明市", "五华区", "人民中路", "春城花园"),
    ("贵州省", "贵阳市", "观山湖区", "金阳南路", "云岭小区"),
    ("甘肃省", "兰州市", "城关区", "庆阳路", "黄河家园"),
    ("海南省", "海口市", "龙华区", "滨海大道", "椰风海岸"),
    ("新疆维吾尔自治区", "乌鲁木齐市", "天山区", "解放北路", "雪莲小区"),
    ("内蒙古自治区", "呼和浩特市", "赛罕区", "大学东街", "草原明珠"),
    ("宁夏回族自治区", "银川市", "金凤区", "北京中路", "塞上雅居"),
    ("青海省", "西宁市", "城西区", "五四西路", "青唐小区"),
    ("福建省", "厦门市", "思明区", "湖滨南路", "鹭岛花园"),
    ("广东省", "广州市", "天河区", "体育西路", "珠江新城"),
    ("浙江省", "宁波市", "鄞州区", "钱湖北路", "东湖花园"),
    ("江苏省", "苏州市", "工业园区", "星湖街", "湖畔小区"),
    ("四川省", "绵阳市", "涪城区", "临园路", "科技城家园"),
    ("陕西省", "咸阳市", "秦都区", "人民西路", "秦风小区"),
    ("河南省", "洛阳市", "洛龙区", "开元大道", "牡丹新苑"),
    ("湖南省", "株洲市", "天元区", "泰山路", "湘水湾"),
    ("湖北省", "宜昌市", "西陵区", "夷陵大道", "三峡家园"),
    ("福建省", "福州市", "鼓楼区", "五四路", "榕城雅居"),
    ("广东省", "佛山市", "南海区", "桂城街道", "岭南公馆"),
    ("浙江省", "温州市", "鹿城区", "车站大道", "瓯江名苑"),
    ("江苏省", "无锡市", "滨湖区", "太湖大道", "湖景花园"),
]

ITEMS = [
    "文件",
    "书籍",
    "衣物",
    "电子配件",
    "生活用品",
    "单肩包",
    "办公用品",
    "学习资料",
    "合同资料",
    "证件复印件",
    "数据线",
    "手机配件",
    "电脑配件",
    "耳机",
    "键盘",
    "鼠标",
    "水杯",
    "雨伞",
    "鞋帽",
    "围巾",
    "玩具",
    "文具",
    "相册",
    "纪念品",
    "护肤品",
    "洗漱用品",
    "厨房用品",
    "家居用品",
    "运动用品",
    "小家电",
    "工具套装",
    "模型摆件",
]
REMARKS = [
    "小心轻放",
    "请勿折叠",
    "易碎物品",
    "无",
    "工作日派送",
    "请电话联系",
    "放门卫处",
    "本人签收",
    "避免受潮",
    "勿压",
    "加急",
    "下午派送",
    "周末可收",
    "到付件",
    "轻拿轻放",
    "注意防水",
    "请勿倒置",
    "外包装完好",
    "可代收",
    "派送前联系",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path_text: str | None, default: Path) -> Path:
    if not path_text:
        return default
    path = Path(path_text)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def choose_font(config: dict[str, Any], font_path: str | None, size: int) -> ImageFont.FreeTypeFont:
    candidates: list[str] = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(config.get("font_candidates", []))

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)

    raise RuntimeError("未找到可用中文字体，请通过 --font-path 指定字体文件。")


def font_for(config: dict[str, Any], font_path: str | None, size: int) -> ImageFont.FreeTypeFont:
    return choose_font(config, font_path, size)


def text_bbox(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont) -> list[int]:
    bbox = draw.multiline_textbbox(xy, text, font=font, spacing=4)
    return [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])]


def split_text(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        current = ""
        for char in paragraph:
            trial = current + char
            width = draw.textlength(trial, font=font)
            if width <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: list[int],
    config: dict[str, Any],
    font_path: str | None,
    font_size: int,
    max_lines: int = 1,
) -> tuple[str, ImageFont.FreeTypeFont]:
    x1, y1, x2, y2 = box
    max_width = x2 - x1
    max_height = y2 - y1
    size = font_size
    while size >= 14:
        font = font_for(config, font_path, size)
        lines = split_text(text, font, draw, max_width)
        if len(lines) <= max_lines:
            fitted = "\n".join(lines)
        else:
            fitted = "\n".join(lines[:max_lines])
        bbox = draw.multiline_textbbox((x1, y1), fitted, font=font, spacing=4)
        if bbox[2] - bbox[0] <= max_width and bbox[3] - bbox[1] <= max_height:
            return fitted, font
        size -= 2
    return text, font_for(config, font_path, 14)


def draw_box_text(
    draw: ImageDraw.ImageDraw,
    config: dict[str, Any],
    font_path: str | None,
    field_config: dict[str, Any],
    text: str,
    fill: str = "black",
) -> list[int]:
    box = [int(v) for v in field_config["box"]]
    font_size = int(field_config.get("font_size", 28))
    max_lines = int(field_config.get("max_lines", 1))
    align = field_config.get("align", "left")
    fitted_text, font = fit_text(draw, text, box, config, font_path, font_size, max_lines)

    x1, y1, x2, _ = box
    text_width = draw.multiline_textbbox((0, 0), fitted_text, font=font, spacing=4)[2]
    x = x1
    if align == "center":
        x = x1 + max(0, (x2 - x1 - text_width) // 2)

    draw.multiline_text((x, y1), fitted_text, font=font, fill=fill, spacing=4)
    return text_bbox(draw, (x, y1), fitted_text, font)


def cover_area(draw: ImageDraw.ImageDraw, cover_box: list[int]) -> None:
    draw.rectangle([int(v) for v in cover_box], fill="white")


def random_name() -> str:
    return random.choice(SURNAMES) + random.choice(GIVEN_NAMES)


def random_phone() -> str:
    prefix = random.choice(["130", "131", "132", "135", "136", "137", "138", "139", "150", "158", "166", "177", "188"])
    return prefix + "".join(str(random.randint(0, 9)) for _ in range(8))


def random_address() -> str:
    province, city, district, road, place = random.choice(ADDRESS_PARTS)
    number = random.randint(1, 188)
    building = random.randint(1, 18)
    room = random.randint(101, 2808)
    return f"{province}{city}{district}{road}{number}号{place}{building}栋{room}室"


def random_digits(length: int) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def build_sample(index: int) -> dict[str, Any]:
    order_time = datetime(2026, 7, 13, 9, 0, 0) + timedelta(minutes=random.randint(0, 480))
    return {
        "tracking_number": random_digits(random.randint(12, 15)),
        "destination_code": random.choice(["712", "029", "0595", "010", "0755", "027"]),
        "receiver_name": random_name(),
        "receiver_phone": random_phone(),
        "receiver_address": random_address(),
        "sender_name": random_name(),
        "sender_phone": random_phone(),
        "sender_address": random_address(),
        "item_name": random.choice(ITEMS),
        "quantity": random.randint(1, 5),
        "remark": random.choice(REMARKS),
        "order_number": random_digits(random.randint(7, 12)),
        "order_time": order_time.strftime("%Y-%m-%d %H:%M:%S"),
        "index": index,
    }


def draw_waybill(
    template_path: Path,
    config: dict[str, Any],
    data: dict[str, Any],
    font_path: str | None,
    preview: bool = False,
) -> tuple[Image.Image, dict[str, list[int]]]:
    image = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    expected_size = tuple(config.get("template_size", []))
    if expected_size and image.size != expected_size:
        print(f"WARNING: template size {image.size} != config size {expected_size}")

    fields = config["fields"]
    boxes: dict[str, list[int]] = {}

    cover_area(draw, fields["tracking_number_top"]["cover_box"])
    boxes["tracking_number"] = draw_box_text(draw, config, font_path, fields["tracking_number_top"], data["tracking_number"])

    draw_box_text(draw, config, font_path, fields["destination_title"], "顺丰特惠")
    draw_box_text(draw, config, font_path, fields["destination_label"], "目的地:")
    draw_box_text(draw, config, font_path, fields["destination_code"], data["destination_code"])

    draw_box_text(draw, config, font_path, fields["receiver_label_main"], "收方:")
    boxes["receiver_address"] = draw_box_text(
        draw, config, font_path, fields["receiver_address_main"], data["receiver_address"]
    )
    identity = f"{data['receiver_name']}    {data['receiver_phone']}"
    identity_box = draw_box_text(draw, config, font_path, fields["receiver_identity_main"], identity)
    boxes["receiver_name"] = [identity_box[0], identity_box[1], identity_box[0] + 90, identity_box[3]]
    boxes["receiver_phone"] = [identity_box[0] + 160, identity_box[1], identity_box[2], identity_box[3]]

    draw_box_text(draw, config, font_path, fields["payment_left"], "月结账号:\n支付方式: 到付")
    draw_box_text(draw, config, font_path, fields["payment_middle"], "代收货款: ￥0元\n卡号:")
    draw_box_text(draw, config, font_path, fields["fee_middle"], "运费: -\n费用合计: -")
    draw_box_text(draw, config, font_path, fields["staff_right"], "收件员:\n寄件日期:\n" + data["order_time"])

    draw_box_text(draw, config, font_path, fields["sender_label_main"], "寄方:")
    boxes["sender_address"] = draw_box_text(draw, config, font_path, fields["sender_address_main"], data["sender_address"])
    sender_identity = f"{data['sender_name']}  {data['sender_phone']}"
    sender_box = draw_box_text(draw, config, font_path, fields["sender_identity_main"], sender_identity)
    boxes["sender_name"] = [sender_box[0], sender_box[1], sender_box[0] + 90, sender_box[3]]
    boxes["sender_phone"] = [sender_box[0] + 95, sender_box[1], sender_box[2], sender_box[3]]
    draw_box_text(draw, config, font_path, fields["ship_time_main"], "寄件日期:\n" + data["order_time"].replace(" ", "\n"))

    draw_box_text(draw, config, font_path, fields["origin_code"], "原寄地: 010")
    draw_box_text(draw, config, font_path, fields["secondary_sender_label"], "寄\n方:")
    draw_box_text(draw, config, font_path, fields["sender_address_secondary"], data["sender_address"])
    draw_box_text(draw, config, font_path, fields["sender_identity_secondary"], sender_identity)
    draw_box_text(draw, config, font_path, fields["secondary_receiver_label"], "收\n方:")
    draw_box_text(draw, config, font_path, fields["receiver_address_secondary"], data["receiver_address"])
    draw_box_text(draw, config, font_path, fields["receiver_identity_secondary"], identity)

    draw_box_text(draw, config, font_path, fields["quantity"], str(data["quantity"]))
    draw_box_text(draw, config, font_path, fields["item_name"], data["item_name"])
    draw_box_text(draw, config, font_path, fields["remark"], data["remark"])
    draw_box_text(draw, config, font_path, fields["order_label"], "订单号")
    draw_box_text(draw, config, font_path, fields["order_number"], data["order_number"])
    draw_box_text(draw, config, font_path, fields["total_fee"], "费用合计:\n- 元")

    if preview:
        preview_font = font_for(config, font_path, 18)
        for name, item in fields.items():
            if "box" not in item:
                continue
            box = [int(v) for v in item["box"]]
            draw.rectangle(box, outline="red", width=2)
            draw.text((box[0], max(0, box[1] - 22)), name, fill="red", font=preview_font)

    return image, boxes


def save_labels(path: Path, labels: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")


def make_label(
    image_path_text: str,
    data: dict[str, Any],
    boxes: dict[str, list[int]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields = {
        "tracking_number": data["tracking_number"],
        "destination_code": data["destination_code"],
        "receiver_name": data["receiver_name"],
        "receiver_phone": data["receiver_phone"],
        "receiver_address": data["receiver_address"],
        "sender_name": data["sender_name"],
        "sender_phone": data["sender_phone"],
        "sender_address": data["sender_address"],
        "item_name": data["item_name"],
        "quantity": data["quantity"],
        "remark": data["remark"],
        "order_number": data["order_number"],
        "order_time": data["order_time"],
    }
    return {
        "image": image_path_text,
        "template_id": "sf_blank_template",
        "fields": fields,
        "main_boxes": boxes,
        "metadata": metadata or {"generated": True},
    }


def add_gaussian_noise(image: Image.Image, sigma: float) -> Image.Image:
    array = np.asarray(image).astype(np.float32)
    noise = np.random.normal(0, sigma, array.shape)
    noisy = np.clip(array + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy, mode="RGB")


def apply_jpeg_compression(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def augment_image(image: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    brightness = round(random.uniform(0.88, 1.12), 3)
    contrast = round(random.uniform(0.90, 1.10), 3)
    noise_sigma = round(random.uniform(2.0, 6.0), 2)
    jpeg_quality = random.randint(65, 88)
    blur_radius = 0.0

    augmented = ImageEnhance.Brightness(image).enhance(brightness)
    augmented = ImageEnhance.Contrast(augmented).enhance(contrast)
    augmented = add_gaussian_noise(augmented, noise_sigma)
    if random.random() < 0.45:
        blur_radius = round(random.uniform(0.25, 0.65), 2)
        augmented = augmented.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    augmented = apply_jpeg_compression(augmented, jpeg_quality)

    metadata = {
        "generated": True,
        "augmented": True,
        "boxes_valid": True,
        "augmentations": {
            "brightness_factor": brightness,
            "contrast_factor": contrast,
            "gaussian_noise_sigma": noise_sigma,
            "gaussian_blur_radius": blur_radius,
            "jpeg_quality": jpeg_quality,
            "rotation": 0,
            "perspective": False,
        },
    }
    return augmented, metadata


def rotate_image(image: Image.Image, angle: float) -> Image.Image:
    return image.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=(255, 255, 255),
    )


def write_split(path: Path, labels: list[dict[str, Any]]) -> None:
    save_labels(path, labels)


def write_dataset_record(
    path: Path,
    clean_count: int,
    augmented_count: int,
    train_count: int,
    val_count: int,
    test_count: int,
    seed: int | None,
) -> None:
    content = f"""# 数据生成记录

## 1. 数据集概况

本次生成虚拟顺丰快递面单数据共 `{clean_count + augmented_count}` 张，其中：

- 干净样本：`{clean_count}` 张
- 增强样本：`{augmented_count}` 张
- 训练集：`{train_count}` 张
- 验证集：`{val_count}` 张
- 测试集：`{test_count}` 张

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

标签文件：

```text
dataset/labels/labels_clean.json
dataset/labels/labels_augmented.json
dataset/labels/train.json
dataset/labels/val.json
dataset/labels/test.json
```

图片路径均以 `dataset/` 为相对根目录记录，例如：

```text
generated/clean/waybill_clean_0001.png
generated/augmented/waybill_aug_0001.png
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
| all | 300 |

生成随机种子：

```text
{seed}
```

## 5. 增强处理

增强样本只使用不改变图像几何位置的处理，因此标签中的主联字段框坐标仍然有效。

增强处理包括：

- 亮度轻微变化：约 `0.88` 到 `1.12`
- 对比度轻微变化：约 `0.90` 到 `1.10`
- 少量高斯噪声：sigma 约 `2.0` 到 `6.0`
- 轻微高斯模糊：部分样本使用，半径约 `0.25` 到 `0.65`
- JPEG 压缩模拟：质量约 `65` 到 `88`

未使用的增强：

- 不旋转
- 不透视变换
- 不裁剪
- 不翻转
- 不做强遮挡

这样可以模拟真实拍摄、压缩和轻微噪声场景，同时避免重新计算 box 坐标。

## 6. 标签说明

每条标签包含：

- `image`：图片相对路径
- `fields`：字段真值，包括收件人、手机号、地址、运单号等
- `main_boxes`：主联关键字段框，格式为 `[x1, y1, x2, y2]`
- `metadata`：生成标记、增强参数、box 是否有效

增强样本的 `metadata.boxes_valid` 为 `true`，因为增强过程未改变文字几何位置。
"""
    path.write_text(content, encoding="utf-8")


def generate_dataset(args: argparse.Namespace) -> None:
    seed = args.seed if args.seed is not None else 20260713
    random.seed(seed)
    np.random.seed(seed)

    template_path = resolve_path(args.template, DEFAULT_TEMPLATE)
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    output_root = resolve_path(args.output_dir, DEFAULT_OUTPUT_DIR)
    labels_root = PROJECT_ROOT / "dataset" / "labels"
    config = load_json(config_path)

    clean_dir = output_root / "clean"
    augmented_dir = output_root / "augmented"
    clean_dir.mkdir(parents=True, exist_ok=True)
    augmented_dir.mkdir(parents=True, exist_ok=True)
    labels_root.mkdir(parents=True, exist_ok=True)

    clean_count = 210
    augmented_count = 90

    clean_labels: list[dict[str, Any]] = []
    clean_images: list[Image.Image] = []
    for index in range(1, clean_count + 1):
        data = build_sample(index)
        image, boxes = draw_waybill(template_path, config, data, args.font_path, preview=False)
        image_name = f"waybill_clean_{index:04d}.png"
        image.save(clean_dir / image_name)
        clean_images.append(image.copy())
        clean_labels.append(
            make_label(
                f"generated/clean/{image_name}",
                data,
                boxes,
                {"generated": True, "augmented": False, "boxes_valid": True},
            )
        )

    augmented_labels: list[dict[str, Any]] = []
    for index in range(1, augmented_count + 1):
        source_image = clean_images[index - 1]
        source_label = clean_labels[index - 1]
        augmented, metadata = augment_image(source_image)
        image_name = f"waybill_aug_{index:04d}.png"
        augmented.save(augmented_dir / image_name)
        label = {
            **source_label,
            "image": f"generated/augmented/{image_name}",
            "metadata": metadata,
        }
        augmented_labels.append(label)

    train_labels = clean_labels[:150] + augmented_labels[:60]
    val_labels = clean_labels[150:180] + augmented_labels[60:75]
    test_labels = clean_labels[180:210] + augmented_labels[75:90]

    random.shuffle(train_labels)
    random.shuffle(val_labels)
    random.shuffle(test_labels)

    save_labels(labels_root / "labels_clean.json", clean_labels)
    save_labels(labels_root / "labels_augmented.json", augmented_labels)
    write_split(labels_root / "train.json", train_labels)
    write_split(labels_root / "val.json", val_labels)
    write_split(labels_root / "test.json", test_labels)
    write_dataset_record(
        DEFAULT_DATASET_RECORD,
        clean_count,
        augmented_count,
        len(train_labels),
        len(val_labels),
        len(test_labels),
        seed,
    )

    print("dataset generated")
    print(f"clean images: {clean_dir} ({clean_count})")
    print(f"augmented images: {augmented_dir} ({augmented_count})")
    print(f"labels: {labels_root}")
    print(f"record: {DEFAULT_DATASET_RECORD}")


def generate_rotated_dataset(args: argparse.Namespace) -> None:
    seed = args.seed if args.seed is not None else 20260713
    random.seed(seed + 17)
    np.random.seed(seed + 17)

    output_root = resolve_path(args.output_dir, DEFAULT_OUTPUT_DIR)
    labels_root = PROJECT_ROOT / "dataset" / "labels"
    clean_dir = output_root / "clean"
    rotated_dir = output_root / "rotated"
    clean_labels_path = labels_root / "labels_clean.json"

    if not clean_labels_path.exists():
        raise RuntimeError("未找到 labels_clean.json，请先运行 --make-dataset 生成 clean 数据。")

    clean_labels = json.loads(clean_labels_path.read_text(encoding="utf-8"))
    rotated_count = min(args.rotated_count, len(clean_labels))
    rotated_dir.mkdir(parents=True, exist_ok=True)

    rotated_labels: list[dict[str, Any]] = []
    for index, source_label in enumerate(clean_labels[:rotated_count], start=1):
        source_image_name = Path(source_label["image"]).name
        source_image_path = clean_dir / source_image_name
        if not source_image_path.exists():
            raise RuntimeError(f"未找到 clean 图片：{source_image_path}")

        angle = round(random.uniform(args.rotation_min, args.rotation_max), 2)
        if abs(angle) < 1.0:
            angle = 1.2 if angle >= 0 else -1.2

        image = Image.open(source_image_path).convert("RGB")
        rotated = rotate_image(image, angle)
        image_name = f"waybill_rotated_{index:04d}.png"
        rotated.save(rotated_dir / image_name)

        label = {
            **source_label,
            "image": f"generated/rotated/{image_name}",
            "metadata": {
                "generated": True,
                "rotated": True,
                "boxes_valid": False,
                "source_image": source_label["image"],
                "rotation_angle": angle,
                "rotation_expand": False,
                "usage": "robustness_test",
                "note": "旋转后未重新计算 box，字段真值仍可用于 OCR/字段提取测试。",
            },
        }
        rotated_labels.append(label)

    save_labels(labels_root / "labels_rotated.json", rotated_labels)
    save_labels(labels_root / "robustness_test.json", rotated_labels)

    print("rotated dataset generated")
    print(f"rotated images: {rotated_dir} ({len(rotated_labels)})")
    print(f"labels: {labels_root / 'labels_rotated.json'}")
    print(f"robustness: {labels_root / 'robustness_test.json'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic express waybill images.")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--font-path", default=None)
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--labels-path", default=str(DEFAULT_LABELS_PATH))
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--make-dataset", action="store_true", help="Generate the formal 300-image dataset.")
    parser.add_argument("--make-rotated", action="store_true", help="Generate rotated robustness-test images.")
    parser.add_argument("--rotated-count", type=int, default=60)
    parser.add_argument("--rotation-min", type=float, default=-5.0)
    parser.add_argument("--rotation-max", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    template_path = resolve_path(args.template, DEFAULT_TEMPLATE)
    config_path = resolve_path(args.config, DEFAULT_CONFIG)
    output_dir = resolve_path(args.output_dir, DEFAULT_OUTPUT_DIR)
    labels_path = resolve_path(args.labels_path, DEFAULT_LABELS_PATH)

    config = load_json(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.make_dataset:
        generate_dataset(args)
        return

    if args.make_rotated:
        generate_rotated_dataset(args)
        return

    if args.preview:
        random.seed(args.seed if args.seed is not None else 20260713)
        data = build_sample(args.start_index)
        image, _ = draw_waybill(template_path, config, data, args.font_path, preview=True)
        preview_path = output_dir / "template_preview.png"
        image.save(preview_path)
        print(f"preview saved: {preview_path}")
        return

    labels: list[dict[str, Any]] = []
    for offset in range(args.count):
        index = args.start_index + offset
        data = build_sample(index)
        image, boxes = draw_waybill(template_path, config, data, args.font_path, preview=False)
        image_name = f"waybill_{index:04d}.png"
        image_path = output_dir / image_name
        image.save(image_path)
        labels.append(make_label(f"generated/{image_name}", data, boxes))

    save_labels(labels_path, labels)
    print(f"generated: {len(labels)}")
    print(f"images: {output_dir}")
    print(f"labels: {labels_path}")


if __name__ == "__main__":
    main()
