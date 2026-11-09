"""
Гидрация структур категорий бота (constants.CATEGORIES и т.д.) из БД —
единый источник правды: таблицы categories / subcategory_groups / subcategories.
"""

import asyncio
import logging

from sqlalchemy import select

from src.kit.database.service import database_service
from src.models import CategoryModel, SubcategoryModel, SubcategoryGroup

logger = logging.getLogger(__name__)

# Emoji-иконки legacy-констант: DB может хранить пустой icon
_LEGACY_ICONS = {
    "swim": "🏊",
    "bike": "🚴",
    "run": "🏃",
    "electronics": "💻",
    "slots": "🏁",
}


def _apply(db_cats, db_groups, db_subs) -> None:
    from src.bot.settings import constants as c

    c.CATEGORIES.clear()
    c.SUBCATEGORIES.clear()
    c.BIKE_SUBCATEGORY_GROUPS.clear()
    c.SIZE_REQUIRED_SUBCATEGORIES.clear()

    groups_by_cat: dict[str, dict[str, dict]] = {}
    for g in sorted(db_groups, key=lambda x: (x.display_order, x.name)):
        groups_by_cat.setdefault(g.category_key, {})[g.key] = {
            "name": g.name,
            "subcategories": {},
        }

    # --- categories (key -> "icon Название") ---
    for cat in sorted(db_cats, key=lambda x: (x.display_order, x.name)):
        icon = cat.icon or _LEGACY_ICONS.get(cat.key, "")
        if icon and icon in cat.name:
            icon = ""
        c.CATEGORIES[cat.key] = f"{icon} {cat.name}".strip()

    # --- subcategories: in-group into groups, flat into SUBCATEGORIES ---
    flat: dict[str, dict[str, str]] = {}
    for s in sorted(
        db_subs, key=lambda x: (x.category_key, x.display_order, x.name)
    ):
        icon = f"{s.icon} " if s.icon else ""
        display = f"{icon}{s.name}"
        if (
            s.group_key
            and s.group_key in groups_by_cat.get(s.category_key, {})
        ):
            groups_by_cat[s.category_key][s.group_key]["subcategories"][
                s.key
            ] = display
            if s.requires_size:
                c.SIZE_REQUIRED_SUBCATEGORIES.append(s.key)
        else:
            flat.setdefault(s.category_key, {})[s.key] = display
            if s.requires_size:
                c.SIZE_REQUIRED_SUBCATEGORIES.append(s.key)

    # --- SUBCATEGORIES: плоские подкатегории + псевдозаписи групп ---
    for cat_key in c.CATEGORIES:
        entry: dict[str, str] = {}
        for g_key, g in groups_by_cat.get(cat_key, {}).items():
            entry[f"{g_key}_group"] = g["name"]
            if cat_key == "bike":
                c.BIKE_SUBCATEGORY_GROUPS[g_key] = {
                    "name": g["name"],
                    "subcategories": g["subcategories"],
                }
        entry.update(flat.get(cat_key, {}))
        c.SUBCATEGORIES[cat_key] = entry


async def hydrate_categories_from_db() -> None:
    """Перечитывает категории из БД и обновляет константы бота на месте."""
    async with database_service.get_session() as session:
        cats = (
            (
                await session.execute(
                    select(CategoryModel).where(
                        CategoryModel.is_active.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )
        groups = (
            (await session.execute(select(SubcategoryGroup))).scalars().all()
        )
        subs = (
            (
                await session.execute(
                    select(SubcategoryModel).where(
                        SubcategoryModel.is_active.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )

    if cats:
        _apply(cats, groups, subs)


_bg_lock = asyncio.Lock()


async def hydrate_categories_bg() -> None:
    """Неблокирующая гидрация (для вызова из admin-эндпоинтов)."""
    if _bg_lock.locked():
        return
    async with _bg_lock:
        try:
            await hydrate_categories_from_db()
        except Exception:  # noqa: BLE001
            logger.exception("hydrate_categories_from_db failed")
