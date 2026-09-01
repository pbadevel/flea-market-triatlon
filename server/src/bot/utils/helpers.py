"""Файл - с вспомогательными функциями"""
from aiogram.types import FSInputFile


def format_phone_for_display(value: str | None) -> str:
    """
    Форматирование номера телефона для отображения.
    Возвращает строку вида +79161234567. Только ровно 11 цифр (не обрабатывает tg:// и @).
    """
    if not value:
        return ""
    s = str(value).strip()
    # Не форматировать как телефон ссылки Telegram и username
    if "tg://" in s or s.startswith("@"):
        return ""
    digits = "".join(c for c in s if c.isdigit())
    # Считаем телефоном только ровно 11 цифр (российский номер)
    if len(digits) != 11:
        return s
    return "+" + digits


def format_contact_for_display(value: str | None) -> str:
    """
    Форматирование контакта для отображения в сообщении (превью, модерация).
    - Телефон (11 цифр): +79161234567
    - @username: как есть
    - tg://user?id=XXX: HTML-ссылка с текстом «Ссылка» (для пользователей без username)
    """
    if not value:
        return ""
    s = str(value).strip()
    if s.startswith("tg://"):
        return f'<a href="{s}">Ссылка</a>'
    if s.startswith("@"):
        return s
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 11:
        return "+" + digits
    return s


def format_file_id_to_storage_path(file_id: str) -> str:
    return 'uploads/ads/' + file_id + ".jpg"

def get_fsinput_photo(storage_path: str):
    return FSInputFile(storage_path)

def get_full_storage_path(storage_path: str):
    return 'uploads/' + storage_path