import base64
import os
import pytz
import random
import string
from io import BytesIO
from datetime import datetime, UTC

from PIL import Image

from src.enums import QrType


def get_now():
    return datetime.now(UTC)

def get_omsk_now():
    return datetime.now(pytz.timezone('Asia/Omsk'))


def create_base64_qr_data(event_id: int, user_id: int, type: QrType) -> str:
    # 1. Формируем строку по шаблону
    data_string = f"{event_id}:{user_id}:{type}"
    # 2. Кодируем в байты (UTF-8), затем в Base64
    bytes_data = data_string.encode('utf-8')
    base64_bytes = base64.b64encode(bytes_data)
    
    # 3. Декодируем обратно в строку для использования
    return base64_bytes.decode('utf-8')


def parse_base64_qr_data(base64_str: str):
    decoded_bytes = base64.b64decode(base64_str)
    decoded_str = decoded_bytes.decode('utf-8')
    event_id, user_id, type = decoded_str.split(':')
    return int(event_id) if event_id.isdigit() else event_id, int(user_id), type



LOGO_PATH = "assets/logo.png"


def add_logo_to_image(image_bytes: bytes) -> bytes:
    """Добавляет логотип в правый верхний угол. Возвращает JPEG bytes."""
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH)
            logo_w = int(img.width * 0.18)
            logo_h = int(logo.height * (logo_w / logo.width))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            pos = (img.width - logo_w - 15, 15)
            img.paste(logo, pos, logo if logo.mode == "RGBA" else None)
        out = BytesIO()
        img.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except Exception:
        return image_bytes


def crop_center(image_bytes: bytes, size: int = 800) -> bytes:
    """Обрезает квадрат по центру и ресайзит. Возвращает JPEG bytes."""
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        side = min(w, h)
        l = (w - side) // 2
        t = (h - side) // 2
        img = img.crop((l, t, l + side, t + side))
        if side > size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        out = BytesIO()
        img.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except Exception:
        return image_bytes


def generate_card_number(user_id: int) -> str:
    """
    generating like "ANGAR-ST-{timestamp}-{user_id % 10000:04d}-{random_part}"
    
    :param user_id: Description
    :type user_id: int
    :return: Description
    :rtype: str
    """
    timestamp = datetime.now().strftime("%y%m%d")
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"ANGAR-ST-{timestamp}-{user_id % 10000:04d}-{random_part}"
