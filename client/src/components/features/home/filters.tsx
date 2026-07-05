// src/components/features/home/filters.tsx
import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { FilterConfig, AdFilters, SortOption } from '@/types/ad';

interface FiltersProps {
  filters: FilterConfig;
  activeFilters: AdFilters;
  onFilterChange: (filters: Partial<AdFilters>) => void;
}

function toggleInList(list: string[] | undefined, value: string): string[] {
  const current = list ?? [];
  if (current.includes(value)) {
    return current.filter((v) => v !== value);
  }
  return [...current, value];
}

function countActiveFilters(f: AdFilters): number {
  let count = 0;
  count += f.categories?.length ?? 0;
  count += f.subcategories?.length ?? 0;
  count += f.countries?.length ?? 0;
  count += f.cities?.length ?? 0;
  if (f.condition) count += 1;
  if (f.ad_type) count += 1;
  if (f.minPrice !== undefined) count += 1;
  if (f.maxPrice !== undefined) count += 1;
  if (f.sort && f.sort !== 'created_at_desc') count += 1;
  return count;
}

function findSubcategoryLabel(config: FilterConfig, key: string): string {
  for (const cat of config.categories) {
    for (const group of cat.groups ?? []) {
      const item = group.items?.find((i) => i.key === key);
      if (item) return item.label;
    }
    const item = cat.items?.find((i) => i.key === key);
    if (item) return item.label;
  }
  return key;
}

const selectedClass =
  'bg-(--palm)/10 font-medium text-(--palm)';
const defaultClass =
  'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)';

export function Filters({ filters, activeFilters, onFilterChange }: FiltersProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    category: true,
    location: true,
    condition: true,
    price: false,
    sort: true,
  });
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [citySearch, setCitySearch] = useState('');

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const toggleCategory = (categoryKey: string) => {
    const next = toggleInList(activeFilters.categories, categoryKey);
    onFilterChange({ categories: next.length ? next : undefined });
  };

  const toggleSubcategory = (subcategoryKey: string) => {
    const next = toggleInList(activeFilters.subcategories, subcategoryKey);
    onFilterChange({ subcategories: next.length ? next : undefined });
  };

  const toggleCountry = (countryKey: string) => {
    const current = activeFilters.countries ?? [];
    const isRemoving = current.includes(countryKey);
    const nextCountries = toggleInList(current, countryKey);
    let nextCities = activeFilters.cities ?? [];

    if (isRemoving) {
      const removed = filters.countries.find((c) => c.key === countryKey);
      const toRemove = new Set(removed?.cities ?? []);
      nextCities = nextCities.filter((c) => !toRemove.has(c));
    }

    onFilterChange({
      countries: nextCountries.length ? nextCountries : undefined,
      cities: nextCities.length ? nextCities : undefined,
    });
  };

  const toggleCity = (city: string) => {
    const next = toggleInList(activeFilters.cities, city);
    onFilterChange({ cities: next.length ? next : undefined });
  };

  const handleConditionChange = (condition: 'new' | 'used' | 'unknown') => {
    onFilterChange({
      condition: activeFilters.condition === condition ? undefined : condition,
    });
  };

  const handleAdTypeChange = (ad_type: 'sale' | 'rent') => {
    onFilterChange({
      ad_type: activeFilters.ad_type === ad_type ? undefined : ad_type,
    });
  };

  const handlePriceChange = (minPrice?: number, maxPrice?: number) => {
    onFilterChange({ minPrice, maxPrice });
  };

  const handleSortChange = (sort: SortOption) => {
    onFilterChange({ sort: activeFilters.sort === sort ? undefined : sort });
  };

  const clearAll = () => {
    onFilterChange({
      categories: undefined,
      subcategories: undefined,
      countries: undefined,
      cities: undefined,
      condition: undefined,
      ad_type: undefined,
      minPrice: undefined,
      maxPrice: undefined,
      sort: undefined,
    });
  };

  const activeCount = countActiveFilters(activeFilters);

  const availableCities = useMemo(() => {
    const selected = activeFilters.countries ?? [];
    const citySet = new Set<string>();

    if (selected.length > 0) {
      for (const key of selected) {
        const country = filters.countries.find((c) => c.key === key);
        country?.cities?.forEach((city) => citySet.add(city));
      }
    } else {
      filters.default_cities?.forEach((city) => citySet.add(city));
    }

    let cities = [...citySet].sort((a, b) => a.localeCompare(b, 'ru'));
    const q = citySearch.trim().toLowerCase();
    if (q) {
      cities = cities.filter((c) => c.toLowerCase().includes(q));
    }
    return cities;
  }, [activeFilters.countries, filters.countries, filters.default_cities, citySearch]);

  const isCategorySelected = (key: string) =>
    activeFilters.categories?.includes(key) ?? false;

  const isSubcategorySelected = (key: string) =>
    activeFilters.subcategories?.includes(key) ?? false;

  const isCountrySelected = (key: string) =>
    activeFilters.countries?.includes(key) ?? false;

  const isCitySelected = (city: string) =>
    activeFilters.cities?.includes(city) ?? false;

  const renderSelectable = (
    key: string,
    label: string,
    selected: boolean,
    onClick: () => void,
    size: 'sm' | 'md' = 'md',
  ) => (
    <button
      key={key}
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded px-2 py-1.5 transition ${
        size === 'sm' ? 'text-xs' : 'text-sm'
      } ${selected ? selectedClass : defaultClass}`}
    >
      {label}
      {selected && <span className="size-1.5 rounded-full bg-(--palm)" />}
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-(--sea-ink)">Фильтры</h3>
        {activeCount > 0 && (
          <button
            type="button"
            onClick={clearAll}
            className="text-xs text-(--palm) hover:underline"
          >
            Сбросить всё
          </button>
        )}
      </div>

      {activeCount > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {activeFilters.categories?.map((key) => (
            <span
              key={`cat-${key}`}
              className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs"
            >
              {filters.categories.find((c) => c.key === key)?.label ?? key}
              <button
                type="button"
                onClick={() => toggleCategory(key)}
                aria-label="Убрать фильтр"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {activeFilters.subcategories?.map((key) => (
            <span
              key={`sub-${key}`}
              className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs"
            >
              {findSubcategoryLabel(filters, key)}
              <button
                type="button"
                onClick={() => toggleSubcategory(key)}
                aria-label="Убрать фильтр"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {activeFilters.countries?.map((key) => (
            <span
              key={`country-${key}`}
              className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs"
            >
              {filters.countries.find((c) => c.key === key)?.name ?? key}
              <button
                type="button"
                onClick={() => toggleCountry(key)}
                aria-label="Убрать фильтр"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {activeFilters.cities?.map((city) => (
            <span
              key={`city-${city}`}
              className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs"
            >
              {city}
              <button
                type="button"
                onClick={() => toggleCity(city)}
                aria-label="Убрать фильтр"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
          {activeFilters.condition && (
            <span className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs">
              {activeFilters.condition === 'new'
                ? 'Новое'
                : activeFilters.condition === 'used'
                  ? 'Б/У'
                  : 'Не указано'}
              <button
                type="button"
                onClick={() => onFilterChange({ condition: undefined })}
                aria-label="Убрать фильтр"
              >
                <X className="size-3" />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Sort */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('sort')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Сортировка
          {expandedSections.sort ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </button>
        {expandedSections.sort && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {(
              [
                { key: 'created_at_desc', label: 'Сначала новые' },
                { key: 'created_at_asc', label: 'Сначала старые' },
                { key: 'price_asc', label: 'Сначала дешёвые' },
                { key: 'price_desc', label: 'Сначала дорогие' },
              ] as const
            ).map(({ key, label }) =>
              renderSelectable(
                key,
                label,
                (activeFilters.sort ?? 'created_at_desc') === key,
                () => handleSortChange(key),
              ),
            )}
          </div>
        )}
      </div>

      {/* Category */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('category')}
          className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          <span>
            Категория
            <span className="ml-1 text-xs font-normal text-(--sea-ink-soft)">
              (несколько)
            </span>
          </span>
          {expandedSections.category ? (
            <ChevronUp className="size-4 shrink-0" />
          ) : (
            <ChevronDown className="size-4 shrink-0" />
          )}
        </button>
        {expandedSections.category && (
          <div className="space-y-2 border-t border-(--line) p-3">
            {filters.categories.map((cat) => {
              const hasGroups = (cat.groups?.length ?? 0) > 0;
              const hasItems = (cat.items?.length ?? 0) > 0;
              const showArrow = hasGroups || hasItems;
              return (
              <div key={cat.key} className="space-y-1">
                <div className="flex items-center gap-1">
                  {showArrow && (
                    <button
                      type="button"
                      onClick={() => setExpandedGroups(prev => ({ ...prev, [cat.key]: !prev[cat.key] }))}
                      className="shrink-0 p-0.5 text-(--sea-ink-soft) hover:text-(--sea-ink)"
                    >
                      {expandedGroups[cat.key] === false ? (
                        <ChevronDown className="size-3" />
                      ) : (
                        <ChevronUp className="size-3" />
                      )}
                    </button>
                  )}
                  <div className="flex-1">
                    {renderSelectable(
                      `cat-${cat.key}`,
                      cat.label,
                      isCategorySelected(cat.key),
                      () => toggleCategory(cat.key),
                    )}
                  </div>
                </div>
                {expandedGroups[cat.key] !== false && (
                  <>
                    {cat.groups?.map((group) => (
                      <div key={group.name} className="ml-6 space-y-0.5">
                        <div className="text-xs font-medium text-(--sea-ink-soft)">
                          {group.name}
                        </div>
                        {group.items?.map((item) =>
                          renderSelectable(
                            item.key,
                            item.label,
                            isSubcategorySelected(item.key),
                            () => toggleSubcategory(item.key),
                            'sm',
                          ),
                        )}
                      </div>
                    ))}
                    {cat.items && cat.items.length > 0 && (
                      <div className="ml-6 space-y-0.5">
                        {cat.groups?.length ? (
                          <div className="text-xs font-medium text-(--sea-ink-soft)">
                            Прочее
                          </div>
                        ) : null}
                        {cat.items.map((item) =>
                          renderSelectable(
                            item.key,
                            item.label,
                            isSubcategorySelected(item.key),
                            () => toggleSubcategory(item.key),
                            'sm',
                          ),
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Location */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('location')}
          className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          <span>
            Местоположение
            <span className="ml-1 text-xs font-normal text-(--sea-ink-soft)">
              (несколько)
            </span>
          </span>
          {expandedSections.location ? (
            <ChevronUp className="size-4 shrink-0" />
          ) : (
            <ChevronDown className="size-4 shrink-0" />
          )}
        </button>
        {expandedSections.location && (
          <div className="space-y-3 border-t border-(--line) p-3">
            <div>
              <div className="mb-2 text-xs font-medium text-(--sea-ink-soft)">
                Страна
              </div>
              <div className="space-y-1">
                {filters.countries.map((country) => (
                  <button
                    key={country.key}
                    type="button"
                    onClick={() => toggleCountry(country.key)}
                    className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm transition ${
                      isCountrySelected(country.key) ? selectedClass : defaultClass
                    }`}
                  >
                    {country.flag && <span>{country.flag}</span>}
                    {country.name}
                    {isCountrySelected(country.key) && (
                      <span className="ml-auto size-1.5 rounded-full bg-(--palm)" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-2 text-xs font-medium text-(--sea-ink-soft)">
                Город
                {(activeFilters.countries?.length ?? 0) === 0 && (
                  <span className="font-normal"> (все страны)</span>
                )}
              </div>
              <input
                type="search"
                value={citySearch}
                onChange={(e) => setCitySearch(e.target.value)}
                placeholder="Найти город..."
                className="mb-2 w-full rounded border border-(--line) bg-white px-2 py-1.5 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
              />
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {availableCities.length === 0 ? (
                  <p className="px-2 py-1 text-xs text-(--sea-ink-soft)">
                    {citySearch.trim()
                      ? 'Город не найден'
                      : 'Нет городов в объявлениях'}
                  </p>
                ) : (
                  availableCities.map((city) =>
                    renderSelectable(
                      city,
                      city,
                      isCitySelected(city),
                      () => toggleCity(city),
                    ),
                  )
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Condition */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('condition')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Состояние
          {expandedSections.condition ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </button>
        {expandedSections.condition && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {filters.conditions.map((cond) =>
              renderSelectable(
                cond.key,
                cond.label,
                activeFilters.condition === cond.key,
                () =>
                  handleConditionChange(cond.key as 'new' | 'used' | 'unknown'),
              ),
            )}
          </div>
        )}
      </div>

      {/* Ad Type */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('ad_type')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Тип объявления
          {expandedSections.ad_type ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </button>
        {expandedSections.ad_type && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {filters.ad_types.map((type) =>
              renderSelectable(
                type.key,
                type.label,
                activeFilters.ad_type === type.key,
                () => handleAdTypeChange(type.key as 'sale' | 'rent'),
              ),
            )}
          </div>
        )}
      </div>

      {/* Price */}
      <div className="rounded-lg border border-(--line)">
        <button
          type="button"
          onClick={() => toggleSection('price')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Цена
          {expandedSections.price ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
        </button>
        {expandedSections.price && (
          <div className="space-y-3 border-t border-(--line) p-3">
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="От"
                value={activeFilters.minPrice ?? ''}
                onChange={(e) =>
                  handlePriceChange(
                    e.target.value ? Number(e.target.value) : undefined,
                    activeFilters.maxPrice,
                  )
                }
                className="w-full rounded border border-(--line) bg-white px-2 py-1.5 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
              />
              <input
                type="number"
                placeholder="До"
                value={activeFilters.maxPrice ?? ''}
                onChange={(e) =>
                  handlePriceChange(
                    activeFilters.minPrice,
                    e.target.value ? Number(e.target.value) : undefined,
                  )
                }
                className="w-full rounded border border-(--line) bg-white px-2 py-1.5 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
              />
            </div>
            {(activeFilters.minPrice !== undefined ||
              activeFilters.maxPrice !== undefined) && (
              <button
                type="button"
                onClick={() => handlePriceChange(undefined, undefined)}
                className="text-xs text-(--palm) hover:underline"
              >
                Сбросить цену
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
