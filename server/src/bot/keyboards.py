"""
Inline-клавиатуры для бота (портированы из barakholka).
Читают категории из БД через CategoryModel / SubcategoryModel.
"""
from sqlalchemy import select, func

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .texts import *
from src.models import CategoryModel, SubcategoryModel, SubcategoryGroup


# ===========================
#  Главное меню
# ===========================

async def main_menu_kb(user_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура главного меню."""
    from src.kit.database.service import database_service
    from src.models import Ad

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=CATALOG_BTN, callback_data="menu:catalog"),
        InlineKeyboardButton(text=SEARCH_BTN, callback_data="menu:search"),
    )
    builder.row(InlineKeyboardButton(text=CREATE_AD_BTN, callback_data="menu:create_ad"))

    # Счётчик объявлений пользователя
    my_ads_text = MY_ADS_BTN
    if user_id:
        try:
            async with database_service.get_session() as session:
                result = await session.execute(
                    select(func.count()).select_from(Ad).where(Ad.seller_user_id == user_id)
                )
                count = result.scalar() or 0
                my_ads_text = f"{MY_ADS_BTN} ({count})"
        except Exception:
            pass

    builder.row(InlineKeyboardButton(text=my_ads_text, callback_data="menu:my_ads"))
    builder.row(
        InlineKeyboardButton(text=RULES_BTN, callback_data="menu:rules"),
        InlineKeyboardButton(text=SUPPORT_BTN, callback_data="menu:support"),
    )
    return builder.as_markup()


def back_kb(callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text=BACK_BTN, callback_data=callback_data)
    ).as_markup()


def main_menu_btn_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text=MAIN_MENU_BTN, callback_data="menu:main")
    ).as_markup()


def cancel_kb(callback_data: str = "menu:my_ads") -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text=CANCEL_BTN, callback_data=callback_data)
    ).as_markup()


# ===========================
#  Тип объявления
# ===========================

def ad_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=AD_TYPE_SALE_BTN, callback_data="ad_type:sale"))
    builder.row(InlineKeyboardButton(text=AD_TYPE_RENT_BTN, callback_data="ad_type:rent"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:main"))
    return builder.as_markup()


# ===========================
#  Категории / подкатегории
# ===========================

async def categories_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории из БД."""
    from src.kit.database.service import database_service

    builder = InlineKeyboardBuilder()
    async with database_service.get_session() as session:
        result = await session.execute(
            select(CategoryModel)
            .where(CategoryModel.is_active.is_(True))
            .order_by(CategoryModel.display_order)
        )
        cats = result.scalars().all()

        for cat in cats:
            label = f"{cat.icon} {cat.name}" if cat.icon else cat.name
            builder.row(InlineKeyboardButton(text=label, callback_data=f"cat:{cat.key}"))

    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:main"))
    return builder.as_markup()


async def subcategories_kb(category_key: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора подкатегории (с учётом групп)."""
    from src.kit.database.service import database_service

    builder = InlineKeyboardBuilder()

    async with database_service.get_session() as session:
        # Группы
        group_result = await session.execute(
            select(SubcategoryGroup)
            .where(SubcategoryGroup.category_key == category_key)
            .order_by(SubcategoryGroup.display_order)
        )
        groups = group_result.scalars().all()

        # Подкатегории вне групп
        sub_result = await session.execute(
            select(SubcategoryModel)
            .where(
                SubcategoryModel.category_key == category_key,
                SubcategoryModel.is_active.is_(True),
                SubcategoryModel.group_key.is_(None),
            )
            .order_by(SubcategoryModel.display_order)
        )
        free_subs = sub_result.scalars().all()

    # Кнопки групп (раскрываются при нажатии)
    for g in groups:
        label = g.icon + " " + g.name if g.icon else g.name
        builder.row(InlineKeyboardButton(text=label, callback_data=f"sgrp:{category_key}:{g.key}"))

    # Кнопки подкатегорий
    for s in free_subs:
        label = s.icon + " " + s.name if s.icon else s.name
        builder.row(InlineKeyboardButton(text=label, callback_data=f"subcat:{category_key}:{s.key}"))

    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:create_ad"))
    return builder.as_markup()


async def group_subs_kb(category_key: str, group_key: str) -> InlineKeyboardMarkup:
    """Подкатегории внутри группы."""
    from src.kit.database.service import database_service

    builder = InlineKeyboardBuilder()

    async with database_service.get_session() as session:
        result = await session.execute(
            select(SubcategoryModel)
            .where(
                SubcategoryModel.category_key == category_key,
                SubcategoryModel.group_key == group_key,
                SubcategoryModel.is_active.is_(True),
            )
            .order_by(SubcategoryModel.display_order)
        )
        subs = result.scalars().all()

    for s in subs:
        label = s.icon + " " + s.name if s.icon else s.name
        builder.row(InlineKeyboardButton(text=label, callback_data=f"subcat:{category_key}:{s.key}"))

    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data=f"cat:{category_key}"))
    return builder.as_markup()


# ===========================
#  Фото
# ===========================

def photo_kb(photo_count: int, category_key: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    min_photos = 1 if category_key == "slots" else 2

    if photo_count >= min_photos:
        builder.row(InlineKeyboardButton(text=CONTINUE_BTN, callback_data="photo:done"))
    if photo_count > 1:
        builder.row(InlineKeyboardButton(text=DELETE_LAST_PHOTO_BTN, callback_data="photo:delete"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="photo:back"))
    return builder.as_markup()


# ===========================
#  Города / страны
# ===========================

def delivery_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="🚶 Самовывоз", callback_data="delivery:self"),
        InlineKeyboardButton(text="📦 Отправка", callback_data="delivery:ship"),
        InlineKeyboardButton(text=BACK_BTN, callback_data="photo:back"),
    ).as_markup()


def condition_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="♻️ Новое", callback_data="cond:new"),
        InlineKeyboardButton(text="♻️ Б/У", callback_data="cond:used"),
    )
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="cond:back"))
    return builder.as_markup()


def contact_method_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Telegram", callback_data="contact:telegram"))
    builder.row(InlineKeyboardButton(text="📞 Телефон", callback_data="contact:phone"))
    builder.row(InlineKeyboardButton(text="💬 Telegram / 📞 Телефон", callback_data="contact:both"))
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="contact:back"))
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text=CONFIRM_BTN, callback_data="confirm:yes"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="confirm:edit"),
    ).as_markup()


def review_rating_kb(seller_id: int, ad_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ad_part = f":{ad_id}" if ad_id else ""
    builder.row(
        InlineKeyboardButton(text="1⭐", callback_data=f"rate:1"),
        InlineKeyboardButton(text="2⭐", callback_data=f"rate:2"),
        InlineKeyboardButton(text="3⭐", callback_data=f"rate:3"),
        InlineKeyboardButton(text="4⭐", callback_data=f"rate:4"),
        InlineKeyboardButton(text="5⭐", callback_data=f"rate:5"),
        width=5,
    )
    return builder.as_markup()


def skip_kb(callback_data: str = "review:skip") -> InlineKeyboardMarkup:
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text=SKIP_BTN, callback_data=callback_data),
    ).as_markup()


# ===========================
#  Каталог (пагинация)
# ===========================

def catalog_pagination_kb(
    current_page: int,
    total_pages: int,
    prefix: str = "cat",
    category: str = "",
    subcategory: str = "",
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    nav_row = []

    if current_page > 1:
        nav_row.append(InlineKeyboardButton(
            text="◀️", callback_data=f"{prefix}:{category}:{subcategory}:{current_page - 1}"
        ))
    nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(
            text="▶️", callback_data=f"{prefix}:{category}:{subcategory}:{current_page + 1}"
        ))

    if nav_row:
        builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text=BACK_BTN, callback_data="menu:main"))
    return builder.as_markup()


# ===========================
#  Модерация
# ===========================

def moderation_kb(ad_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"moderate:approve:{ad_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"moderate:reject:{ad_id}"),
    )
    return builder.as_markup()
