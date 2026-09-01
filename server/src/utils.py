import base64
import os
import pytz
from io import BytesIO
from datetime import datetime, UTC
from PIL import Image
from aiohttp import ClientSession
from src.enums import QrType
from src.config import settings
from src.models import AdPhoto
from src.services.storage import LocalFileStorage

BOT_TOKEN = settings.BOT_TOKEN.get_secret_value()

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



LOGO_PATH = "src/bot/assets/logo.png"


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


async def _download_from_telegram(file_id: str) -> bytes | None:
    async with ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as resp:
            data = await resp.json()
            if not data.get("ok"):
                print(f"❌ getFile failed for {file_id}: {data.get('description')}")
                return None
            file_path = data["result"]["file_path"]

        # 2. Скачиваем бинарник
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

async def download_file_from_telegram(file_id: str) -> str:
        """
        returns storage_path to photo
        """
        file_bytes = await _download_from_telegram(file_id) # pyright: ignore

        if not file_bytes:
            raise
            
        # Определяем расширение (Telegram не отдаёт его в API, подставляем .jpg по умолчанию или парсишь content-type)
        storage_path = await LocalFileStorage().save(
            file_bytes=file_bytes, 
            filename=file_id, 
            extension=".jpg"
        )
        return storage_path
        # ✅ id={record.id} -> {storage_path}