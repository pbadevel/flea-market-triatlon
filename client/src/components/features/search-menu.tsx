import { Search } from "lucide-react";

const popularSearches = [
  "Garmin Fenix 7",
  "Garmin Forerunner 955",
  "Garmin Edge 530",
  "Garmin Striker 4",
  "Пульсометр",
  "Велосипедный компьютер",
];

const recentSearches = [
  "Garmin Instinct 2",
  "Зарядное устройство",
];

export function SearchMenu() {
  return (
    <div className="absolute left-0 top-full z-50 mt-2 w-100 rounded-xl border border-(--line) bg-(--bg-base) p-4 shadow-xl">
      {/* Recent searches */}
      {recentSearches.length > 0 && (
        <div className="mb-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
            Недавние запросы
          </h3>
          <ul className="space-y-1">
            {recentSearches.map((search) => (
              <li key={search}>
                <button className="w-full rounded-lg px-3 py-2 text-left text-sm text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)">
                  {search}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Popular searches */}
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
          Популярное
        </h3>
        <ul className="space-y-1">
          {popularSearches.map((search) => (
            <li key={search}>
              <button className="group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)">
                <Search className="size-4 opacity-0 transition group-hover:opacity-50" />
                {search}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}