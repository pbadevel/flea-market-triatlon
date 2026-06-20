"""Email notification service for flea-market."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import settings
from src.logging import get_logger

log = get_logger()


class EmailService:
    """Send emails (SMTP). Settings come from config — empty SMTP_HOST = disabled."""

    def is_enabled(self) -> bool:
        return bool(settings.SMTP_HOST) and bool(settings.SMTP_FROM)

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """Send an HTML email. Returns True on success."""
        if not self.is_enabled():
            log.warning("Email service disabled — cannot send to %s", to)
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [to], msg.as_string())

            log.info("Email sent to %s: %s", to, subject)
            return True
        except Exception as e:
            log.error("Failed to send email to %s: %s", to, e, exc_info=True)
            return False

    async def notify_user_ad_approved_email(self, email: str, title: str, price: int, ad_id: int) -> bool:
        """Send approval notification via email."""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2ecc71;">✅ Ваше объявление одобрено!</h2>
            <p><b>{title}</b></p>
            <p>💰 {price:,} ₽</p>
            <p>Объявление опубликовано в канале и доступно на сайте.</p>
            <p style="margin-top: 20px; color: #888; font-size: 12px;">
                С уважением, команда барахолки
            </p>
        </body>
        </html>
        """
        return await self.send_email(
            to=email,
            subject=f"✅ Объявление «{title}» одобрено",
            html_body=html,
        )

    async def notify_user_ad_rejected_email(self, email: str, title: str, price: int, reason: str) -> bool:
        """Send rejection notification via email."""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #e74c3c;">❌ Ваше объявление отклонено</h2>
            <p><b>{title}</b></p>
            <p>💰 {price:,} ₽</p>
            <p>Причина: <b>{reason}</b></p>
            <p>Вы можете исправить объявление и отправить на повторную модерацию.</p>
            <p style="margin-top: 20px; color: #888; font-size: 12px;">
                С уважением, команда барахолки
            </p>
        </body>
        </html>
        """
        return await self.send_email(
            to=email,
            subject=f"❌ Объявление «{title}» отклонено",
            html_body=html,
        )


email_service = EmailService()
