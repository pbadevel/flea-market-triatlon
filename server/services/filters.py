"""
Service for category / filter configuration.
Reads categories from DB (CategoryModel, SubcategoryModel, SubcategoryGroup).
If DB is empty, falls back to static defaults (first run / migration).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models import CategoryModel, SubcategoryModel, SubcategoryGroup as SubcategoryGroupModel
from src.schemas.filters import (
    FilterConfig,
    CategoryFilter,
    SubcategoryItem,
    SubcategoryGroup,
    GeoItem,
)

# --- Static fallback (used if DB categories are empty) ---
_STATIC_CATEGORIES = {
    "swim": {
        "label": "🏊 ПЛАВАНИЕ",
        "items": [
            {"key": "wetsuits", "label": "Гидрокостюмы", "requires_size": True},
            {"key": "accessories", "label": "Аксессуары"},
        ],
    },
    "bike": {
        "label": "🚴 ВЕЛОСПОРТ",
        "groups": [
            {
                "name": "🚲 Велосипеды",
                "items": [
                    {"key": "bicycles_tt", "label": "TT", "requires_size": True},
                    {"key": "bicycles_road", "label": "Шоссе", "requires_size": True},
                    {"key": "bicycles_other", "label": "Остальные", "requires_size": True},
                ],
            },
            {
                "name": "👕 Экипировка",
                "items": [
                    {"key": "equipment_shoes", "label": "👟 Велообувь", "requires_size": True},
                    {"key": "equipment_wear", "label": "👕 Велодежда", "requires_size": True},
                    {"key": "equipment_helmets", "label": "🪖 Шлемы и Очки", "requires_size": True},
                ],
            },
        ],
        "items": [
            {"key": "wheels", "label": "🛞 Колёса"},
            {"key": "components", "label": "⚙️ Запчасти"},
            {"key": "accessories", "label": "🔧 Аксессуары"},
            {"key": "bike_bag", "label": "🧳 Велочемоданы"},
        ],
    },
    "run": {
        "label": "🏃 БЕГ",
        "items": [
            {"key": "shoes", "label": "👟 Кроссовки", "requires_size": True},
            {"key": "clothing", "label": "👕 Одежда для бега", "requires_size": True},
            {"key": "accessories", "label": "🎒 Аксессуары"},
        ],
    },
    "electronics": {
        "label": "💻 ЭЛЕКТРОНИКА",
        "items": [
            {"key": "watches", "label": "⌚ Часы"},
            {"key": "bike_computers", "label": "📱 Велокомпьютеры"},
            {"key": "sensors", "label": "📡 Датчики и мощемеры"},
            {"key": "smart_trainers", "label": "🏋️ Смарт-станки"},
        ],
    },
    "slots": {
        "label": "🏁 СТАРТОВЫЕ СЛОТЫ",
        "items": [],
    },
}

GEO_COUNTRIES = [
    {"key": "russia", "name": "Россия", "flag": "🇷🇺", "cities": ["Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Казань", "Нижний Новгород", "Самара", "Ростов-на-Дону", "Краснодар", "Сочи", "Уфа", "Челябинск", "Пермь", "Тюмень", "Омск", "Воронеж", "Красноярск", "Ижевск", "Калининград", "Владивосток"]},
    {"key": "belarus", "name": "Беларусь", "flag": "🇧🇾", "cities": ["Минск", "Гомель", "Витебск", "Могилёв"]},
    {"key": "kazakhstan", "name": "Казахстан", "flag": "🇰🇿", "cities": ["Алматы", "Астана", "Шымкент", "Караганда"]},
    {"key": "armenia", "name": "Армения", "flag": "🇦🇲", "cities": ["Ереван", "Гюмри", "Ванадзор", "Вагаршапат"]},
    {"key": "georgia", "name": "Грузия", "flag": "🇬🇪", "cities": ["Тбилиси", "Кутаиси", "Батуми", "Рустави"]},
    {"key": "azerbaijan", "name": "Азербайджан", "flag": "🇦🇿", "cities": ["Баку", "Гянджа", "Сумгайыт", "Ленкорань"]},
    {"key": "uzbekistan", "name": "Узбекистан", "flag": "🇺🇿", "cities": ["Ташкент", "Самарканд", "Наманган", "Бухара"]},
    {"key": "cyprus", "name": "Кипр", "flag": "🇨🇾", "cities": ["Лимасол", "Никосия"]},
    {"key": "singapore", "name": "Singapore", "flag": "🇸🇬", "cities": ["Singapore"]},
]

DEFAULT_CITIES = [
    "Москва", "Санкт-Петербург", "Сочи", "Краснодар", "Казань",
    "Екатеринбург", "Новосибирск", "Нижний Новгород", "Самара",
    "Ростов-на-Дону", "Уфа", "Челябинск", "Пермь", "Тюмень",
    "Омск", "Воронеж", "Красноярск", "Ижевск", "Калининград", "Владивосток",
]

CONDITIONS = [{"key": "new", "label": "Новое"}, {"key": "used", "label": "Б/У"}, {"key": "unknown", "label": "Не указано"}]
AD_TYPES = [{"key": "sale", "label": "Продажа"}, {"key": "rent", "label": "Аренда"}]
SIZES = ["44", "46", "48", "50", "52", "54", "56", "58", "60"]


def _sort_cities(cities: set[str]) -> list[str]:
    return sorted(cities, key=lambda c: c.casefold())


async def _load_cities_from_ads(
    session: AsyncSession,
) -> tuple[dict[str, set[str]], list[str]]:
    """Distinct cities from approved ads, grouped by country key."""
    from src.models import Ad, AdStatus

    stmt = (
        select(Ad.country, Ad.city)
        .where(
            Ad.status == AdStatus.approved,
            Ad.city.isnot(None),
            Ad.city != "",
        )
        .group_by(Ad.country, Ad.city)
    )
    result = await session.execute(stmt)

    by_country: dict[str, set[str]] = {}
    all_cities: set[str] = set()

    for country, city in result.all():
        city = city.strip()
        if not city:
            continue
        all_cities.add(city)
        country_key = country if country else "_other"
        by_country.setdefault(country_key, set()).add(city)

    return by_country, all_cities


async def _load_categories_from_db(session: AsyncSession) -> list[dict]:
    """Load category tree from DB models."""
    result = await session.execute(
        select(CategoryModel)
        .where(CategoryModel.is_active.is_(True))
        .options(
            joinedload(CategoryModel.subcategories),
            joinedload(CategoryModel.groups),
        )
        .order_by(CategoryModel.display_order)
    )
    categories_db = result.unique().scalars().all()

    if not categories_db:
        # Fallback to static
        return _STATIC_CATEGORIES  # type: ignore

    output = []
    for cat in categories_db:
        cat_data = {
            "key": cat.key,
            "label": cat.name,
            "icon": cat.icon,
            "items": [],
            "groups": [],
        }

        # Build group structure
        groups_map = {}
        for group in cat.groups:
            groups_map[group.key] = {
                "name": group.name,
                "items": [],
            }

        # Sort subcategories into groups or items
        for sub in cat.subcategories:
            item = SubcategoryItem(
                key=sub.key,
                label=sub.name,
                requires_size=sub.requires_size,
            )
            if sub.group_key and sub.group_key in groups_map:
                groups_map[sub.group_key]["items"].append(item)
            else:
                cat_data["items"].append(item.model_dump())

        cat_data["groups"] = [
            SubcategoryGroup(**g) for g in groups_map.values() if g["items"]
        ]

        output.append(cat_data)

    return output


async def get_filter_config(session: AsyncSession) -> FilterConfig:
    categories_data = await _load_categories_from_db(session)

    categories = [
        CategoryFilter(
            key=cat["key"],
            label=cat["label"],
            icon=cat.get("icon"),
            groups=cat.get("groups") or None,
            items=[SubcategoryItem(**i) for i in cat.get("items", [])] or None,
        )
        for cat in categories_data
    ]

    countries = [GeoItem(**c) for c in GEO_COUNTRIES]

    config = FilterConfig(
        categories=categories,
        countries=countries,
        default_cities=list(DEFAULT_CITIES),
        conditions=CONDITIONS,
        sizes=SIZES,
        ad_types=AD_TYPES,
    )

    by_country, all_cities = await _load_cities_from_ads(session)

    known_country_keys = {c.key for c in config.countries}
    other_cities = set(by_country.pop("_other", set()))

    for country in config.countries:
        db_cities = by_country.get(country.key, set())
        country.cities = _sort_cities(set(country.cities) | db_cities)

    for key, cities in by_country.items():
        if key not in known_country_keys:
            other_cities |= cities

    config.default_cities = _sort_cities(
        set(config.default_cities) | all_cities | other_cities
    )

    return config
