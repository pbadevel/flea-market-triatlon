// src/components/features/home/filters.tsx
import { useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { FilterConfig, AdFilters, SortOption } from '@/types/ad';

interface FiltersProps {
  filters: FilterConfig;
  activeFilters: AdFilters;
  onFilterChange: (filters: Partial<AdFilters>) => void;
}

export function Filters({ filters, activeFilters, onFilterChange }: FiltersProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    category: true,
    location: true,
    condition: true,
    price: false,
    sort: true,
  });


  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleCategoryChange = (category: string, subcategory?: string) => {
    onFilterChange({ 
      category: category === activeFilters.category ? undefined : category,
      subcategory: subcategory === activeFilters.subcategory ? undefined : subcategory 
    });
  };

  const handleLocationChange = (country?: string, city?: string) => {
    onFilterChange({ 
      country: country === activeFilters.country ? undefined : country,
      city: city === activeFilters.city ? undefined : city 
    });
  };

  const handleConditionChange = (condition?: 'new' | 'used' | "unknown") => {
    onFilterChange({ condition: condition === activeFilters.condition ? undefined : condition });
  };

  const handleAdTypeChange = (ad_type?: 'sale' | 'rent') => {
    onFilterChange({ ad_type: ad_type === activeFilters.ad_type ? undefined : ad_type });
  };

  const handlePriceChange = (minPrice?: number, maxPrice?: number) => {
    onFilterChange({ minPrice, maxPrice });
  };

  const handleSortChange = (sort?: SortOption) => {
    onFilterChange({ sort: sort === activeFilters.sort ? undefined : sort });
  };

  const clearAll = () => {
    onFilterChange({
      category: undefined,
      subcategory: undefined,
      country: undefined,
      city: undefined,
      condition: undefined,
      ad_type: undefined,
      minPrice: undefined,
      maxPrice: undefined,
      sort: undefined,
    });
  };

  const activeCount = Object.values(activeFilters).filter(v => v !== undefined).length;

  // console.log(filters)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-(--sea-ink)">Фильтры</h3>
        {activeCount > 0 && (
          <button
            onClick={clearAll}
            className="text-xs text-(--palm) hover:underline"
          >
            Сбросить всё
          </button>
        )}
      </div>

      {/* Active filters chips */}
      {activeCount > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {activeFilters.category && (
            <span className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs">
              {filters.categories.find(c => c.key === activeFilters.category)?.label}
              <button onClick={() => onFilterChange({ category: undefined })}>
                <X className="size-3" />
              </button>
            </span>
          )}
          {activeFilters.city && (
            <span className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs">
              {activeFilters.city}
              <button onClick={() => onFilterChange({ city: undefined })}>
                <X className="size-3" />
              </button>
            </span>
          )}
          {activeFilters.condition && (
            <span className="inline-flex items-center gap-1 rounded-full bg-(--link-bg-hover) px-2 py-0.5 text-xs">
              {activeFilters.condition === 'new' ? 'Новое' : activeFilters.condition === 'used' ? 'Б/У' : 'Не указано'}
              <button onClick={() => onFilterChange({ condition: undefined })}>
                <X className="size-3" />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Sort */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('sort')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Сортировка
          {expandedSections.sort ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.sort && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {[
              { key: 'created_at_desc', label: 'Сначала новые' },
              { key: 'created_at_asc', label: 'Сначала старые' },
              { key: 'price_asc', label: 'Сначала дешёвые' },
              { key: 'price_desc', label: 'Сначала дорогие' },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => handleSortChange(key as SortOption)}
                className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-sm transition ${
                  activeFilters.sort === key
                    ? 'bg-(--palm)/10 font-medium text-(--palm)'
                    : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                }`}
              >
                {label}
                {activeFilters.sort === key && (
                  <span className="size-1.5 rounded-full bg-(--palm)" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Category */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('category')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Категория
          {expandedSections.category ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.category && (
          <div className="space-y-2 border-t border-(--line) p-3">
            {filters.categories.map(cat => (
              <div key={cat.key} className="space-y-1">
                <button
                  onClick={() => handleCategoryChange(cat.key)}
                  className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-sm transition ${
                    activeFilters.category === cat.key && !activeFilters.subcategory
                      ? 'bg-(--palm)/10 font-medium text-(--palm)'
                      : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                  }`}
                >
                  {cat.label}
                  {activeFilters.category === cat.key && !activeFilters.subcategory && (
                    <span className="size-1.5 rounded-full bg-(--palm)" />
                  )}
                </button>
                {cat.groups?.map(group => (
                  <div key={group.name} className="ml-4 space-y-0.5">
                    <div className="text-xs font-medium text-(--sea-ink-soft)">{group.name}</div>
                    {group.items?.map(item => (
                      <button
                        key={item.key}
                        onClick={() => handleCategoryChange(cat.key, item.key)}
                        className={`flex w-full items-center justify-between rounded px-2 py-1 text-xs transition ${
                          activeFilters.subcategory === item.key
                            ? 'bg-(--palm)/10 font-medium text-(--palm)'
                            : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                        }`}
                      >
                        {item.label}
                        {activeFilters.subcategory === item.key && (
                          <span className="size-1.5 rounded-full bg-(--palm)" />
                        )}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Location */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('location')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Местоположение
          {expandedSections.location ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.location && (
          <div className="space-y-3 border-t border-(--line) p-3">
            {/* Country */}
            <div>
              <div className="mb-2 text-xs font-medium text-(--sea-ink-soft)">Страна</div>
              <div className="space-y-1">
                {filters.countries.map(country => (
                  <button
                    key={country.key}
                    onClick={() => handleLocationChange(country.key)}
                    className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm transition ${
                      activeFilters.country === country.key && !activeFilters.city
                        ? 'bg-(--palm)/10 font-medium text-(--palm)'
                        : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                    }`}
                  >
                    {country.flag && <span>{country.flag}</span>}
                    {country.name}
                    {activeFilters.country === country.key && !activeFilters.city && (
                      <span className="ml-auto size-1.5 rounded-full bg-(--palm)" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* City */}
            {activeFilters.country && (
              <div>
                <div className="mb-2 text-xs font-medium text-(--sea-ink-soft)">Город</div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {filters.countries
                    .find(c => c.key === activeFilters.country)
                    ?.cities?.map(city => (
                      <button
                        key={city}
                        onClick={() => handleLocationChange(undefined, city)}
                        className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-sm transition ${
                          activeFilters.city === city
                            ? 'bg-(--palm)/10 font-medium text-(--palm)'
                            : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                        }`}
                      >
                        {city}
                        {activeFilters.city === city && (
                          <span className="size-1.5 rounded-full bg-(--palm)" />
                        )}
                      </button>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Condition */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('condition')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Состояние
          {expandedSections.condition ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.condition && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {filters.conditions.map(cond => (
              <button
                key={cond.key}
                onClick={() => handleConditionChange(cond.key as 'new' | 'used' | 'unknown')}
                className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-sm transition ${
                  activeFilters.condition === cond.key
                    ? 'bg-(--palm)/10 font-medium text-(--palm)'
                    : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                }`}
              >
                {cond.label}
                {activeFilters.condition === cond.key && (
                  <span className="size-1.5 rounded-full bg-(--palm)" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Ad Type */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('ad_type')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Тип объявления
          {expandedSections.ad_type ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.ad_type && (
          <div className="space-y-1 border-t border-(--line) p-3">
            {filters.ad_types.map(type => (
              <button
                key={type.key}
                onClick={() => handleAdTypeChange(type.key as 'sale' | 'rent')}
                className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-sm transition ${
                  activeFilters.ad_type === type.key
                    ? 'bg-(--palm)/10 font-medium text-(--palm)'
                    : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover)'
                }`}
              >
                {type.label}
                {activeFilters.ad_type === type.key && (
                  <span className="size-1.5 rounded-full bg-(--palm)" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Price */}
      <div className="rounded-lg border border-(--line)">
        <button
          onClick={() => toggleSection('price')}
          className="flex w-full items-center justify-between px-3 py-2.5 text-sm font-medium text-(--sea-ink)"
        >
          Цена
          {expandedSections.price ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        </button>
        {expandedSections.price && (
          <div className="space-y-3 border-t border-(--line) p-3">
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="От"
                value={activeFilters.minPrice || ''}
                onChange={(e) => handlePriceChange(
                  e.target.value ? Number(e.target.value) : undefined,
                  activeFilters.maxPrice
                )}
                className="w-full rounded border border-(--line) bg-white px-2 py-1.5 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
              />
              <input
                type="number"
                placeholder="До"
                value={activeFilters.maxPrice || ''}
                onChange={(e) => handlePriceChange(
                  activeFilters.minPrice,
                  e.target.value ? Number(e.target.value) : undefined
                )}
                className="w-full rounded border border-(--line) bg-white px-2 py-1.5 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
              />
            </div>
            {(activeFilters.minPrice || activeFilters.maxPrice) && (
              <button
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