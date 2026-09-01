"""
Файл - содержащий переменные окружения
"""

import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Файл .env отсутствует')
else:
    load_dotenv()


"""Токен бота"""
BOT_TOKEN = os.environ.get('BOT_TOKEN')

"""База данных"""
DATABASE_URL = os.environ.get('DATABASE_URL')

"""Поддержка"""
LOG_CHAT_ID = os.environ.get('LOG_CHAT_ID')
SUPPORT_USER_ID = int(os.environ.get('SUPPORT_USER_ID', '0'))
SUPPORT_USERNAME = os.environ.get('SUPPORT_USER', '').replace('@', '')  # username без @

"""Авторизация"""
AUTHORIZATION_TOKEN = os.environ.get('AUTHORIZATION_TOKEN')

"""ID разработчиков для отправки ошибок"""
DEVELOPER_IDS = [int(dev_id.strip()) for dev_id in os.environ.get('DEVELOPER_IDS', '').split(',') if dev_id.strip()]

"""ID администраторов (автоматически становятся модераторами)"""
ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.environ.get('ADMIN_IDS', '').split(',') if admin_id.strip()]

"""Модерация и публикация"""
MODERATION_CHAT_ID = int(os.environ.get('MODERATION_CHAT_ID', '0'))
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', '0'))
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME')
BOT_USERNAME = os.environ.get('BOT_USERNAME', '')

"""Оферта"""
OFERTA_URL = os.environ.get('OFERTA_URL', '')

"""Тест-режим (TEST_MODE=1 в .env)
Все временные интервалы сильно урезаны для быстрого тестирования:
  - Обычный продавец: интервал автоподнятия 30 мин
  - Доверенный продавец: интервал 15 мин
  - Первое напоминание: за 5 мин до next_boost_at
  - Повторные напоминания: каждые 10 мин
  - Авто-пауза: 35 мин без ответа
  - Авто-деактивация: 30 мин после последнего поднятия
Управляется ТОЛЬКО через .env"""
_TEST_MODE_RAW = os.environ.get('TEST_MODE', '0')
TEST_MODE = str(_TEST_MODE_RAW).strip().lower() in ("1", "true", "yes", "on")