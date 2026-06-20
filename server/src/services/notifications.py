"""Умное оповещение: Telegram → fallback email."""
from src.models import Ad, AdStatus, User
from src.bot.tg_services import tg_service_notifier
from src.services.email import email_service
from src.logging import get_logger

log = get_logger()


async def notify_ad_approved(ad: Ad):
    """Оповестить об одобрении: TG → fallback email."""
    seller = ad.seller
    if not seller:
        log.warning("notify_ad_approved: no seller for ad %s", ad.id)
        return

    # Пробуем Telegram
    if seller.username:
        try:
            await tg_service_notifier.notify_user_ad_approved(ad)
            log.info("Approved: TG notified %s (ad %s)", seller.username, ad.id)
            return
        except Exception as e:
            log.warning("Approved: TG failed for %s: %s, fallback to email", seller.username, e)

    # Fallback на email
    email = _get_email(seller)
    if email:
        await email_service.notify_user_ad_approved_email(
            email=email,
            title=ad.title,
            price=ad.price,
            ad_id=ad.id,
        )
        log.info("Approved: email sent to %s (ad %s)", email, ad.id)
    else:
        log.warning("Approved: no contact method for seller %s (ad %s)", seller.id, ad.id)


async def notify_ad_rejected(ad: Ad, reason: str):
    """Оповестить об отклонении: TG → fallback email."""
    seller = ad.seller
    if not seller:
        log.warning("notify_ad_rejected: no seller for ad %s", ad.id)
        return

    # Пробуем Telegram
    if seller.username:
        try:
            await tg_service_notifier.notify_user_ad_rejected(ad, reason)
            log.info("Rejected: TG notified %s (ad %s)", seller.username, ad.id)
            return
        except Exception as e:
            log.warning("Rejected: TG failed for %s: %s, fallback to email", seller.username, e)

    # Fallback на email
    email = _get_email(seller)
    if email:
        await email_service.notify_user_ad_rejected_email(
            email=email,
            title=ad.title,
            price=ad.price,
            reason=reason,
        )
        log.info("Rejected: email sent to %s (ad %s)", email, ad.id)
    else:
        log.warning("Rejected: no contact method for seller %s (ad %s)", seller.id, ad.id)


def _get_email(user: User) -> str | None:
    """Получить email пользователя из credentials."""
    if user.credentials and user.credentials.email:
        return user.credentials.email
    return None
