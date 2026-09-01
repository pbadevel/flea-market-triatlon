"""
Утилиты для форматирования карточек объявлений в канале.

Форматы:
  - Активная (продажа):  <b>Title (Size)</b> / 💰 price ₽  ✅Доверенный / 📍 City · Б/У / #tags
  - Активная (аренда):   <b>Title (Size)</b> / ♻️ price ₽/сут ✅ Доверенный / 📍 City / #tags #Аренда
  - Изменение цены:      <b>Title (Size)</b> / 🏷️ price ₽  Доверенный / 📍 City · Condition / #tags
  - Архивная:            Title (Size) / price ₽ / City · Б/У  (без форматирования, без кнопки)

Правила хэштегов (п.2.2):
  - Только 9 городов получают тег: Москва, СПб, Сочи, Самара, Екб, НН, Красноярск, Владивосток, Казань
  - Нет тегов #Продажа / #БУ / #Новое — только #Аренда для аренды
  - Порядок: [категория/подкатегория] [город] [#Аренда]
"""

from loguru import logger

from src.bot.settings.constants import CONDITIONS, CITY_NAME_TO_HASHTAG


# ---------------------------------------------------------------------------
# Хэштеги по категориям и подкатегориям
# Правила:
#   swim       → #Плавание  (+ #Гидрокостюмы для wetsuits)
#   bike       → категорию НЕ тегируем, только подкатегории:
#                  bicycles_tt   → #Велосипеды #ТТ
#                  bicycles_road → #Велосипеды #Шоссе
#                  bicycles_other → #Велосипеды
#                  wheels        → #Колеса
#                  equipment_*   → #ВелоЭкип + (#ВелоОбувь | #ВелоОдежда | #ШлемаОчки)
#                  components    → #ВелоЗапчасти
#                  accessories   → #ВелоАксессуары
#                  bike_bag      → #ВелоЧемоданы
#   run        → #Бег  (+ #Кроссовки | #Одежда | #Аксессуары)
#   electronics → #Электроника (+ #Часы | #Велокомп | #Тренажеры | #Датчики)
#   slots       → #Слоты
# ---------------------------------------------------------------------------

def _category_tags(category: str, subcategory: str) -> list[str]:
    """Вернуть список хэштегов для категории и подкатегории."""
    sub = subcategory or ""

    if category == "swim":
        tags = ["#Плавание"]
        if sub == "wetsuits":
            tags.append("#Гидрокостюмы")
        return tags

    if category == "bike":
        # Велосипеды
        if sub in ("bicycles_tt", "bicycles_road", "bicycles_other"):
            tags = ["#Велосипеды"]
            if sub == "bicycles_tt":
                tags.append("#ТТ")
            elif sub == "bicycles_road":
                tags.append("#Шоссе")
            # bicycles_other → только #Велосипеды
            return tags
        if sub == "wheels":
            return ["#Колеса"]
        if sub in ("equipment_shoes", "equipment_wear", "equipment_helmets"):
            tags = ["#ВелоЭкип"]
            if sub == "equipment_shoes":
                tags.append("#ВелоОбувь")
            elif sub == "equipment_wear":
                tags.append("#ВелоОдежда")
            elif sub == "equipment_helmets":
                tags.append("#ШлемаОчки")
            return tags
        if sub == "components":
            return ["#ВелоЗапчасти"]
        if sub == "accessories":
            return ["#ВелоАксессуары"]
        if sub == "bike_bag":
            return ["#ВелоЧемоданы"]
        # Для bike без подкатегории или неизвестной подкатегории — без тега
        return []

    if category == "run":
        tags = ["#Бег"]
        if sub == "shoes":
            tags.append("#Кроссовки")
        elif sub == "clothing":
            tags.append("#Одежда")
        elif sub == "accessories":
            tags.append("#Аксессуары")
        return tags

    if category == "electronics":
        tags = ["#Электроника"]
        if sub == "watches":
            tags.append("#Часы")
        elif sub == "bike_computers":
            tags.append("#Велокомп")
        elif sub == "smart_trainers":
            tags.append("#Тренажеры")
        elif sub == "sensors":
            tags.append("#Датчики")
        return tags

    if category == "slots":
        return ["#Слоты"]

    return []


def _get_city_hashtag(city: str) -> str:
    """Хэштег для города — только для 9 перечисленных городов, иначе пустая строка."""
    return CITY_NAME_TO_HASHTAG.get(city or "", "")


def _build_hashtags(ad) -> str:
    """Сформировать строку хэштегов для карточки."""
    tags = _category_tags(
        getattr(ad, "category", "") or "",
        getattr(ad, "subcategory", "") or "",
    )

    city_tag = _get_city_hashtag(getattr(ad, "city", "") or "")
    if city_tag:
        tags.append(city_tag)

    if getattr(ad, "ad_type", "Продажа") == "Аренда":
        tags.append("#Аренда")

    return " ".join(tags)


# ---------------------------------------------------------------------------
# Форматирование строк карточек
# ---------------------------------------------------------------------------

def _title_line(ad, bold: bool = True) -> str:
    """Первая строка: название (размер в скобках)."""
    title = ad.title or ""
    size = getattr(ad, "size", None)
    text = f"{title} ({size})" if size else title
    return f"<b>{text}</b>" if bold else text


def format_active_caption(ad, seller_is_trusted: bool) -> str:
    """
    Формат активной карточки (продажа или аренда).

    Продажа:
        <b>Canyon Speedmax CFR M (54)</b>
        💰 450 000 ₽  ✅Доверенный
        📍 Москва · Б/У
        #Велосипеды #ТТ #Мск

    Аренда:
        <b>Canyon Speedmax CFR M (54)</b>
        ♻️ 4500 ₽/сут ✅ Доверенный
        📍 Санкт-Петербург
        #Велосипеды #ТТ #СПб #Аренда
    """
    ad_type = getattr(ad, "ad_type", "Продажа")
    price_formatted = f"{ad.price:,}".replace(",", " ")
    condition_display = CONDITIONS.get(getattr(ad, "condition", ""), "")

    line1 = _title_line(ad, bold=True)
    trusted_str = "  ✅ Доверенный" if seller_is_trusted else ""

    if ad_type == "Аренда":
        line2 = f"♻️ {price_formatted} ₽/сут{trusted_str}"
        line3 = f"📍 {ad.city}"
    else:
        line2 = f"💰 {price_formatted} ₽{trusted_str}"
        line3 = f"📍 {ad.city} · {condition_display}" if condition_display else f"📍 {ad.city}"

    # Теги при создании/публикации объявления не добавляем
    lines = [line1, line2, line3]
    return "\n".join(lines)


def format_price_change_caption(ad, seller_is_trusted: bool) -> str:
    """
    Формат карточки при изменении цены (значок 🏷️, «Доверенный» без ✅).

        <b>Canyon Speedmax CFR (54)</b>
        🏷️ 430 000 ₽  Доверенный
        📍 Санкт-Петербург · Новое
        #Велосипеды #ТТ #СПб
    """
    ad_type = getattr(ad, "ad_type", "Продажа")
    price_formatted = f"{ad.price:,}".replace(",", " ")
    condition_display = CONDITIONS.get(getattr(ad, "condition", ""), "")

    line1 = _title_line(ad, bold=True)
    trusted_str = "  Доверенный" if seller_is_trusted else ""

    if ad_type == "Аренда":
        # Для аренды сохраняем арендный эмодзи и формат цены за сутки
        line2 = f"♻️ {price_formatted} ₽/сут{trusted_str}"
        line3 = f"📍 {ad.city}"
    else:
        line2 = f"🏷️ {price_formatted} ₽{trusted_str}"
        line3 = f"📍 {ad.city} · {condition_display}" if condition_display else f"📍 {ad.city}"
    lines = [line1, line2, line3]
    # Теги при изменении цены не добавляем
    return "\n".join(lines)


def format_archive_caption(ad) -> str:
    """
    Формат архивной (неактивной) карточки — только заголовок.

    🔒 ЗАКРЫТО
    <b>Шапочка арена</b>
    """
    line1 = "🔒 ЗАКРЫТО"
    line2 = _title_line(ad, bold=True)
    return "\n".join([line1, line2])


def _channel_targets():
    """Возможные адреса канала для запросов Telegram.

    Для удаления сообщений числовой CHANNEL_ID надёжнее, чем @username,
    поэтому пробуем оба варианта."""
    from src.bot.settings.settings import CHANNEL_ID, CHANNEL_USERNAME

    targets = []
    if CHANNEL_ID:
        targets.append(CHANNEL_ID)
    if CHANNEL_USERNAME:
        targets.append(f"@{CHANNEL_USERNAME}")
    return targets or [CHANNEL_ID]


async def remove_or_archive_channel_post(ad, *, reason: str = "") -> bool:
    """Убрать пост объявления из канала при закрытии/снятии с публикации.

    Логика:
      - если с публикации прошло < 48 ч — удаляем сообщение из канала;
      - если удалить не удалось (нет прав / ошибка Telegram) или прошло ≥ 48 ч —
        переводим карточку в архивный формат «ЗАКРЫТО» без кнопок.

    Возвращает True, если сообщение действительно удалено из канала,
    иначе False (карточка переведена в «ЗАКРЫТО» либо ничего не делали).
    """
    from datetime import datetime, timezone, timedelta
    from src.bot.database.methods import update_ad
    from src.bot.loader import bot

    if not getattr(ad, "channel_message_id", None):
        return False

    targets = _channel_targets()

    pub_at = getattr(ad, "published_at", None) or getattr(ad, "created_at", None)
    if pub_at is not None and pub_at.tzinfo is None:
        pub_at = pub_at.replace(tzinfo=timezone.utc)
    within_48h = pub_at is not None and (datetime.now(timezone.utc) - pub_at) < timedelta(hours=48)

    if within_48h:
        last_err = None
        for target in targets:
            try:
                await bot.delete_message(chat_id=target, message_id=ad.channel_message_id)
                await update_ad(ad.id, channel_message_id=None)
                logger.info(f"Сообщение объявления #{ad.id} удалено из канала ({reason}, <48ч)")
                return True
            except Exception as e:
                last_err = e
        logger.warning(
            f"Не удалось удалить сообщение объявления #{ad.id} из канала (<48ч), "
            f"перевожу в «ЗАКРЫТО»: {last_err}. "
            f"Проверьте право бота can_delete_messages в канале."
        )

    # Фолбэк: архивный формат «ЗАКРЫТО»
    caption = format_archive_caption(ad)
    last_err = None
    for target in targets:
        try:
            await bot.edit_message_caption(
                chat_id=target,
                message_id=ad.channel_message_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=None,
            )
            logger.info(f"Сообщение объявления #{ad.id} в канале: формат «ЗАКРЫТО» ({reason})")
            return False
        except Exception as e:
            last_err = e
    logger.warning(f"Не удалось обновить сообщение в канале для объявления #{ad.id}: {last_err}")
    return False
