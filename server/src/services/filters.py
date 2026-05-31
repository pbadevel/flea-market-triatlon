from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Ad, AdStatus
from src.schemas.filters import (
    FilterConfig,
    CategoryFilter,
    CategoryKey,
    SubcategoryItem,
    SubcategoryGroup,
    GeoItem,
)

CATEGORIES_DATA: dict[str, Any] = {
    "swim": {
        "label": "🏊 ПЛАВАНИЕ",
        "items": [
            {"key": "wetsuits", "label": "Гидрокостюмы", "requires_size": True},
            {"key": "accessories", "label": "Аксессуары"},
        ],
        "tags": ["swim", "wetsuit", "goggles", "buoy", "swim_accessory"],
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
        "tags": ["bike", "roadbike", "ttbike", "gravelbike", "mtb", "wheels", "tires", "components", "helmet", "cyclingwear", "cycling_shoes", "tools"],
    },
    "run": {
        "label": "🏃 БЕГ",
        "items": [
            {"key": "shoes", "label": "👟 Кроссовки", "requires_size": True},
            {"key": "clothing", "label": "👕 Одежда для бега", "requires_size": True},
            {"key": "accessories", "label": "🎒 Аксессуары"},
        ],
        "tags": ["run", "running_shoes", "running_wear", "hydration", "run_accessory"],
    },
    "electronics": {
        "label": "💻 ЭЛЕКТРОНИКА",
        "items": [
            {"key": "watches", "label": "⌚ Часы"},
            {"key": "bike_computers", "label": "📱 Велокомпьютеры"},
            {"key": "sensors", "label": "📡 Датчики и мощемеры"},
            {"key": "smart_trainers", "label": "🏋️ Смарт-станки"},
        ],
        "tags": ["electronics", "watch", "bikecomputer", "sensor", "heart_rate", "trainer", "smart_trainer"],
    },
    "slots": {
        "label": "🏁 СТАРТОВЫЕ СЛОТЫ",
        "items": [],
        "tags": ["race_slot", "ironman", "ironman70_3", "triathlon", "race"],
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
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Казань",
    "Нижний Новгород", "Самара", "Ростов-на-Дону", "Краснодар", "Сочи",
    "Уфа", "Челябинск", "Пермь", "Тюмень", "Омск", "Воронеж",
    "Красноярск", "Ижевск", "Калининград", "Владивосток"
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


def _build_static_filter_config() -> FilterConfig:
    categories = []
    for key, raw_data in CATEGORIES_DATA.items():
        data: dict[str, Any] = raw_data
        groups = [SubcategoryGroup(**g) for g in data.get("groups", [])] or None
        items = [SubcategoryItem(**i) for i in data.get("items", [])] or None
        categories.append(
            CategoryFilter(
                key=cast(CategoryKey, key),
                label=data["label"],
                groups=groups,
                items=items,
                default_tags=data.get("tags", []),
            )
        )

    countries = [GeoItem(**c) for c in GEO_COUNTRIES]

    return FilterConfig(
        categories=categories,
        countries=countries,
        default_cities=list(DEFAULT_CITIES),
        conditions=CONDITIONS,
        sizes=SIZES,
        ad_types=AD_TYPES,
    )


async def get_filter_config(session: AsyncSession) -> FilterConfig:
    config = _build_static_filter_config()
    by_country, all_cities = await _load_cities_from_ads(session)

    known_country_keys = {c.key for c in config.countries}
    other_cities = set(by_country.pop("_other", set()))

    for country in config.countries:
        db_cities = by_country.get(country.key, set())
        country.cities = _sort_cities(set(country.cities) | db_cities)

    # Cities with unknown / missing country — still selectable
    for key, cities in by_country.items():
        if key not in known_country_keys:
            other_cities |= cities

    config.default_cities = _sort_cities(
        set(config.default_cities) | all_cities | other_cities
    )

    return config