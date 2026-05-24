from typing import Any, cast
from src.schemas.filters import (
    FilterConfig, CategoryFilter, CategoryKey,
    SubcategoryItem, SubcategoryGroup, GeoItem
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
    {"key": "belarus", "name": "Беларусь", "flag": "🇧🇾", "cities": ["Минск", "Гомель", "Витебск", "Могилёв"]},
    {"key": "kazakhstan", "name": "Казахстан", "flag": "🇰🇿", "cities": ["Алматы", "Астана", "Шымкент", "Караганда"]},
    {"key": "armenia", "name": "Армения", "flag": "🇦🇲", "cities": ["Ереван", "Гюмри", "Ванадзор", "Вагаршапат"]},
    {"key": "georgia", "name": "Грузия", "flag": "🇬🇪", "cities": ["Тбилиси", "Кутаиси", "Батуми", "Рустави"]},
    {"key": "azerbaijan", "name": "Азербайджан", "flag": "🇦🇿", "cities": ["Баку", "Гянджа", "Сумгайыт", "Ленкорань"]},
    {"key": "uzbekistan", "name": "Узбекистан", "flag": "🇺🇿", "cities": ["Ташкент", "Самарканд", "Наманган", "Бухара"]},
]

DEFAULT_CITIES = [
    "Москва", "Санкт-Петербург", "Екатеринбург", "Новосибирск", "Казань",
    "Нижний Новгород", "Самара", "Ростов-на-Дону", "Краснодар", "Сочи",
    "Уфа", "Челябинск", "Пермь", "Тюмень", "Омск", "Воронеж",
    "Красноярск", "Ижевск", "Калининград", "Владивосток"
]

CONDITIONS = [{"key": "new", "label": "Новое"}, {"key": "used", "label": "Б/У"}]
AD_TYPES = [{"key": "sale", "label": "Продажа"}, {"key": "rent", "label": "Аренда"}]
SIZES = ["44", "46", "48", "50", "52", "54", "56", "58", "60"]

def get_filter_config() -> FilterConfig:
    categories = []
    for key, raw_data in CATEGORIES_DATA.items():
        data: dict[str, Any] = raw_data
        groups = [SubcategoryGroup(**g) for g in data.get("groups", [])] or None
        items = [SubcategoryItem(**i) for i in data.get("items", [])] or None
        categories.append(CategoryFilter(
            key=cast(CategoryKey, key),
            label=data["label"],
            groups=groups,
            items=items,
            default_tags=data.get("tags", []),
        ))

    countries = [GeoItem(**c) for c in GEO_COUNTRIES]

    return FilterConfig(
        categories=categories,
        countries=countries,
        default_cities=DEFAULT_CITIES,
        conditions=CONDITIONS,
        sizes=SIZES,
        ad_types=AD_TYPES,
    )