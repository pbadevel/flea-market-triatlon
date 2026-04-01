// src/components/features/home/mobile-catalog.tsx
import { Link } from "@tanstack/react-router";
import { X, ChevronRight } from "lucide-react";
import { useMobileCatalog } from "@/components/features/mobile-catalog-provider";

const catalogData = [
  {
    name: "Все объявления",
    count: 318,
    subcategories: [
      { name: "Все товары", to: "/catalog/all" },
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


export function MobileCatalog() {
  const { isOpen, close } = useMobileCatalog();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-100 lg:hidden">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={close}
      />
      
      {/* Menu Panel */}
      <div className="absolute right-0 top-0 h-full w-[85%] max-w-sm overflow-y-auto bg-(--header-bg) shadow-xl">
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-(--line) p-4">
          <h2 className="text-lg font-semibold text-(--sea-ink)">Каталог</h2>
          <button
            onClick={close}
            className="rounded-lg p-2 text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
            aria-label="Закрыть"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Categories */}
        <div className="p-2">
          {catalogData.map((category) => (
            <div key={category.name} className="mb-1">
              <div className="flex items-center justify-between rounded-lg px-3 py-3 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{category.name}</span>
                </div>
                {category.count && (
                  <span className="rounded-full bg-(--chip-bg) px-2 py-0.5 text-xs text-(--sea-ink-soft)">
                    {category.count}
                  </span>
                )}
              </div>
              
              {/* Subcategories */}
              {category.subcategories && (
                <div className="ml-4 mr-2 mb-1 space-y-0.5 border-l-2 border-(--line) pl-4">
                  {category.subcategories.map((sub) => (
                    <Link
                      key={sub.to}
                      to={sub.to}
                      onClick={close}
                      className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
                    >
                      <ChevronRight className="size-4" />
                      {sub.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}