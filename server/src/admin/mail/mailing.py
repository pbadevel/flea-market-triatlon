from src.kit.utils import get_bot




class AdminMailer:
    def __init__(self):
        self.bot = get_bot()

    async def send(self, message, user_id):
        await self.bot.send_message(
            chat_id=user_id,
            text=message
        )

    # NOT READY