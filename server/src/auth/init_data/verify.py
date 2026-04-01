import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from src.config import settings


def verify_init_data(init_data_raw: str) -> bool:
    init_data_dict = dict(parse_qsl(init_data_raw, strict_parsing=True))

    received_hash = init_data_dict.pop("hash", None)

    auth_date_str = init_data_dict.get("auth_date")
    if not auth_date_str or not auth_date_str.isdigit():
        return False

    now_timestamp = int(time.time())
    expires_at_ts = int(auth_date_str) + 86400

    if expires_at_ts < now_timestamp:
        return False

    pairs = [f"{key}={value}" for key, value in sorted(init_data_dict.items())]
    check_string = "\n".join(pairs)

    expected_hash = sign_data(check_string)

    return expected_hash == received_hash


def sign_data(data: str) -> str:
    data_bytes = data.encode("utf-8")
    secret_key = hash_token(settings.BOT_TOKEN.get_secret_value())
    signature = hmac.new(secret_key, data_bytes, hashlib.sha256)

    return signature.hexdigest()


def hash_token(token: str) -> bytes:
    token_bytes = token.encode("utf-8") if isinstance(token, str) else token
    return hmac.new(b"WebAppData", token_bytes, hashlib.sha256).digest()
