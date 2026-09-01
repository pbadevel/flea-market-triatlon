"""Файл - запуск веб-сервера"""

from aiohttp import web
from .routes import setup_routes


async def init_app():
    """
    Инициализирует приложение aiohttp с подключёнными маршрутами.

    :return: Web Application
    """
    app = web.Application()
    setup_routes(app)
    return app


def main():
    """
    Запускает веб-сервер с настройками.
    """
    app = init_app()
    web.run_app(app, host="0.0.0.0", port=8080)  # TODO: Разобраться с портом и хостом при необходимости


if __name__ == "__main__":
    main()
