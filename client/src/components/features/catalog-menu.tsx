// src/components/features/home/catalog-menu.tsx
import { Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";

const catalogData = [
  {
    name: "Все объявления",
    count: 318,
    subcategories: [
      { name: "Все товары", to: "/catalog/all" },
      { name: "Новинки", to: "/catalog/new" },
      { name: "Распродажа", to: "/catalog/sale" },
    ],
  },
  {
    name: "Аренда",
    count: null,
    subcategories: [
      { name: "Смарт-часы", to: "/rent/smartwatches" },
      { name: "Велосипеды", to: "/rent/bikes" },
      { name: "Эхолоты", to: "/rent/fishfinders" },
    ],
  },
  {
    name: "ПЛАВАНИЕ",
    count: 16,
    subcategories: [
      { name: "Часы для плавания", to: "/swimming/watches" },
      { name: "Пульсометры", to: "/swimming/heart-rate" },
      { name: "Очки для плавания", to: "/swimming/goggles" },
      { name: "Аксессуары", to: "/swimming/accessories" },
    ],
  },
  {
    name: "ВЕЛОСПОРТ",
    count: 223,
    subcategories: [
      { name: "Велокомпьютеры", to: "/cycling/computers" },
      { name: "Пульсометры", to: "/cycling/heart-rate" },
      { name: "Радары", to: "/cycling/radars" },
      { name: "Датчики скорости", to: "/cycling/speed-sensors" },
      { name: "Датчики каденса", to: "/cycling/cadence-sensors" },
      { name: "Крепления", to: "/cycling/mounts" },
    ],
  },
  {
    name: "БЕГ",
    count: 24,
    subcategories: [
      { name: "Беговые часы", to: "/running/watches" },
      { name: "Пульсометры", to: "/running/heart-rate" },
      { name: "Шагомеры", to: "/running/steps" },
      { name: "Аксессуары", to: "/running/accessories" },
    ],
  },
  {
    name: "ЭЛЕКТРОНИКА",
    count: 39,
    subcategories: [
      { name: "Смарт-часы", to: "/electronics/smartwatches" },
      { name: "Фитнес-браслеты", to: "/electronics/fitness-bands" },
      { name: "Наушники", to: "/electronics/headphones" },
      { name: "Зарядные устройства", to: "/electronics/chargers" },
      { name: "Кабели", to: "/electronics/cables" },
    ],
  },
  {
    name: "СТАРТОВЫЕ СЛОТЫ",
    count: 16,
    subcategories: [
      { name: "Марафоны", to: "/slots/marathons" },
      { name: "Триатлон", to: "/slots/triathlon" },
      { name: "Велозаезды", to: "/slots/cycling" },
      { name: "Заплывы", to: "/slots/swimming" },
    ],
  },
];

export function CatalogMenu() {
  return (
    <div className="absolute left-0 top-full z-50 mt-2 w-200 rounded-xl border bg-(--bg-base) border-(--line) p-6 shadow-xl">
      <div className="grid grid-cols-3 gap-6">
        {catalogData.map((category) => (
          <div key={category.name}>
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-sm font-semibold text-(--sea-ink)">
                {category.name}
              </h3>
              {category.count && (
                <span className="rounded-full bg-(--chip-bg) px-2 py-0.5 text-xs text-(--sea-ink-soft)">
                  {category.count}
                </span>
              )}
            </div>
            <ul className="space-y-2">
              {category.subcategories.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className="group flex items-center gap-2 text-sm text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
                  >
                    <ChevronRight className="size-4 opacity-0 transition group-hover:opacity-100" />
                    {item.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}