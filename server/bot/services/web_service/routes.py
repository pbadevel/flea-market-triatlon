"""Файл - с маршрутами"""

from aiohttp import web

from src.bot.loader import bot
from src.bot.settings.settings import AUTHORIZATION_TOKEN


async def send_notification(request):
    """
    Обработчик для отправки уведомлений.

    :param request: HTTP запрос
    :return: HTTP Ответ с информацией об успехе операции
    """
    data = await request.json()
    chat_id = data.get("chat_id")
    message = data.get("message")
    authorization_token = data.get("authorization_token")
    if authorization_token != AUTHORIZATION_TOKEN:
        return web.json_response({"status": "error", "message": "Invalid authorization token"})
    await bot.send_message(chat_id, message)

    return web.json_response({"status": "success", "message": "Notification sent"})


async def health_check(request):
    """
    Простая проверка состояния сервера.

    :param request: HTTP запрос
    :return: HTTP ответ о состоянии сервера
    """
    return web.json_response({"status": "ok"})


def setup_routes(app):
    """
    Регистрирует маршруты на приложение aiohttp.

    :param app: Web Application
    """
    app.router.add_post("/api/v1/notify", send_notification)
    app.router.add_get("/api/v1/health", health_check)
