"""
Seeder: переносит структуру категорий/подкатегорий из старого бота в новые DB-модели.

Запуск: uv run python -m scripts.seed_categories
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень сервера в path, чтобы импорты работали
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from src.kit.database.service import database_service
from src.models import CategoryModel, SubcategoryModel, SubcategoryGroup


# Константы из старого бота (barakholka/settings/constants.py)
CATEGORIES = {
    "swim": {"name": "🏊 ПЛАВАНИЕ", "icon": "🏊", "order": 1},
    "bike": {"name": "🚴 ВЕЛОСПОРТ", "icon": "🚴", "order": 2},
    "run": {"name": "🏃 БЕГ", "icon": "🏃", "order": 3},
    "electronics": {"name": "💻 ЭЛЕКТРОНИКА", "icon": "💻", "order": 4},
    "slots": {"name": "🏁 СТАРТОВЫЕ СЛОТЫ", "icon": "🏁", "order": 5},
}

BIKE_SUBCATEGORY_GROUPS = {
    "bicycles": {
        "name": "🚲 Велосипеды",
        "order": 1,
        "subcategories": {
            "bicycles_tt": {"name": "TT", "size": True},
            "bicycles_road": {"name": "Шоссе", "size": True},
            "bicycles_other": {"name": "Остальные", "size": True},
        }
    },
    "equipment": {
        "name": "👕 Экипировка",
        "order": 2,
        "subcategories": {
            "equipment_shoes": {"name": "👟 Велообувь", "size": True},
            "equipment_wear": {"name": "👕 Велодежда", "size": True},
            "equipment_helmets": {"name": "🪖 Шлемы и Очки", "size": True},
        }
    },
}

SUBCATEGORIES = {
    "swim": {
        "wetsuits": {"name": "Гидрокостюмы", "order": 1, "size": True},
        "accessories": {"name": "Аксессуары", "order": 2, "size": False},
    },
    "bike": {
        "wheels": {"name": "🛞 Колёса", "order": 100, "size": False},
        "components": {"name": "⚙️ Запчасти", "order": 101, "size": False},
        "accessories": {"name": "🔧 Аксессуары", "order": 102, "size": False},
        "bike_bag": {"name": "🧳 Велочемоданы", "order": 103, "size": False},
    },
    "run": {
        "shoes": {"name": "👟 Кроссовки", "order": 1, "size": True},
        "clothing": {"name": "👕 Одежда для бега", "order": 2, "size": True},
        "accessories": {"name": "🎒 Аксессуары", "order": 3, "size": False},
    },
    "electronics": {
        "watches": {"name": "⌚ Часы", "order": 1, "size": False},
        "bike_computers": {"name": "📱 Велокомпьютеры", "order": 2, "size": False},
        "sensors": {"name": "📡 Датчики и мощемеры", "order": 3, "size": False},
        "smart_trainers": {"name": "🏋️ Смарт-станки", "order": 4, "size": False},
    },
    "slots": {},  # без подкатегорий
}


async def seed():
    async with database_service.get_session() as session:
        # --- Категории ---
        for key, info in CATEGORIES.items():
            result = await session.execute(
                select(CategoryModel).where(CategoryModel.key == key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = info["name"]
                existing.icon = info["icon"]
                existing.display_order = info["order"]
            else:
                session.add(CategoryModel(
                    key=key, name=info["name"], icon=info["icon"],
                    display_order=info["order"], is_active=True
                ))
        await session.flush()

        # --- Группы (bike) ---
        for group_key, ginfo in BIKE_SUBCATEGORY_GROUPS.items():
            result = await session.execute(
                select(SubcategoryGroup).where(SubcategoryGroup.key == group_key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = ginfo["name"]
                existing.display_order = ginfo["order"]
            else:
                session.add(SubcategoryGroup(
                    key=group_key, name=ginfo["name"],
                    display_order=ginfo["order"],
                    category_key="bike"
                ))
        await session.flush()

        # --- Подкатегории ---
        for cat_key, subs in SUBCATEGORIES.items():
            for sub_key, sinfo in subs.items():
                # Проверяем, к какой группе относится
                group_key = None
                for gk, ginfo in BIKE_SUBCATEGORY_GROUPS.items():
                    if sub_key in ginfo["subcategories"]:
                        group_key = gk
                        break

                result = await session.execute(
                    select(SubcategoryModel).where(
                        SubcategoryModel.key == sub_key,
                        SubcategoryModel.category_key == cat_key
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.name = sinfo["name"]
                    existing.requires_size = sinfo.get("size", False)
                    existing.display_order = sinfo.get("order", 50)
                    existing.group_key = group_key
                else:
                    session.add(SubcategoryModel(
                        key=sub_key, name=sinfo["name"],
                        icon=sinfo.get("icon"),
                        display_order=sinfo.get("order", 50),
                        requires_size=sinfo.get("size", False),
                        is_active=True,
                        category_key=cat_key,
                        group_key=group_key,
                    ))

        # --- Подкатегории из групп (bike) ---
        for group_key, ginfo in BIKE_SUBCATEGORY_GROUPS.items():
            for sub_key, sinfo in ginfo["subcategories"].items():
                result = await session.execute(
                    select(SubcategoryModel).where(
                        SubcategoryModel.key == sub_key,
                        SubcategoryModel.category_key == "bike"
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.name = sinfo["name"]
                    existing.requires_size = sinfo.get("size", False)
                    existing.display_order = ginfo["order"]
                    existing.group_key = group_key
                else:
                    session.add(SubcategoryModel(
                        key=sub_key, name=sinfo["name"],
                        display_order=ginfo["order"],
                        requires_size=sinfo.get("size", False),
                        is_active=True,
                        category_key="bike",
                        group_key=group_key,
                    ))

        await session.commit()
        print("✅ Категории и подкатегории засеяны!")


if __name__ == "__main__":
    asyncio.run(seed())
