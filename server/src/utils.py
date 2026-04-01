import base64
import pytz
import random
import string
from datetime import datetime, UTC
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
