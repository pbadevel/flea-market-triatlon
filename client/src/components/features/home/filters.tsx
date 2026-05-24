// src/components/features/home/filters.tsx
import { useState } from 'react';
import { ChevronDown, ChevronRight, Check } from 'lucide-react';
import { FilterConfig } from '@/types/ad';

interface FiltersProps {
  filters: FilterConfig;
  activeFilters: {
    category?: string;
    subcategory?: string;
    country?: string;
    city?: string;
    minPrice?: number;
    maxPrice?: number;
  };
  onFilterChange: (filters: {
    category?: string;
    subcategory?: string;
    country?: string;
    city?: string;
    minPrice?: number;
    maxPrice?: number;
    page?: number;
  }) => void;
}

export function Filters({ filters, activeFilters, onFilterChange }: FiltersProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    activeFilters.category ? new Set([activeFilters.category]) : new Set()
  );

  const toggleCategory = (categoryKey: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryKey)) {
      newExpanded.delete(categoryKey);
    } else {
      newExpanded.add(categoryKey);
    }
    setExpandedCategories(newExpanded);
  };

  const handleCategorySelect = (categoryKey: string | undefined) => {
    onFilterChange({
      category: categoryKey,
      subcategory: undefined,
      page: 1,
    });
  };

  const handleSubcategorySelect = (subcategoryKey: string | undefined) => {
    onFilterChange({
      subcategory: subcategoryKey,
      page: 1,
    });
  };

  const handleCountrySelect = (countryKey: string | undefined) => {
    onFilterChange({
      country: countryKey,
      page: 1,
    });
  };

  return (
    <div className="space-y-5">
      {/* Categories */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-(--sea-ink-soft)">
          Категории
        </h3>
        <div className="space-y-1">
          {/* ALL button for categories */}
          <button
            onClick={() => handleCategorySelect(undefined)}
            className={`group flex w-full items-center justify-between rounded px-3 py-2 text-sm transition-all ${
              !activeFilters.category
                ? 'bg-(--palm)/10 text-(--palm) font-medium'
                : 'text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            <span>Все</span>
            {!activeFilters.category && <Check className="size-3.5 shrink-0" />}
          </button>

          {filters.categories.map((category) => {
            const hasSubitems = category.groups?.length || category.items?.length;
            const isExpanded = expandedCategories.has(category.key);
            const isSelected = activeFilters.category === category.key;

            return (
              <div key={category.key} className="space-y-1">
                {/* Category button */}
                <button
                  onClick={() => {
                    handleCategorySelect(category.key);
                    if (hasSubitems) toggleCategory(category.key);
                  }}
                  className={`group flex w-full items-center justify-between rounded px-3 py-2 text-sm transition-all ${
                    isSelected
                      ? 'bg-(--palm)/10 text-(--palm) font-medium'
                      : 'text-(--sea-ink) hover:bg-(--link-bg-hover)'
                  }`}
                >
                  <span className="truncate">{category.label}</span>
                  <div className="flex items-center gap-1">
                    {isSelected && <Check className="size-3.5 shrink-0" />}
                    {hasSubitems && (
                      <ChevronRight
                        className={`size-3.5 shrink-0 transition-transform ${
                          isExpanded ? 'rotate-90' : ''
                        }`}
                      />
                    )}
                  </div>
                </button>

                {/* Subcategories */}
                {hasSubitems && isExpanded && (
                  <div className="ml-4 space-y-1 border-l border-(--line) pl-3">
                    {/* Groups */}
                    {category.groups?.map((group) => (
                      <div key={group.name} className="space-y-1">
                        <div className="px-3 py-1 text-xs font-medium text-(--sea-ink-soft)">
                          {group.name}
                        </div>
                        {group.items.map((item) => {
                          const isSubSelected = activeFilters.subcategory === item.key;
                          return (
                            <button
                              key={item.key}
                              onClick={() => handleSubcategorySelect(item.key)}
                              className={`group flex w-full items-center justify-between rounded px-3 py-1.5 text-sm transition-all ${
                                isSubSelected
                                  ? 'bg-(--palm)/10 text-(--palm) font-medium'
                                  : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)'
                              }`}
                            >
                              <span className="truncate">{item.label}</span>
                              {isSubSelected && <Check className="size-3.5 shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    ))}

                    {/* Regular items */}
                    {category.items?.map((item) => {
                      const isSubSelected = activeFilters.subcategory === item.key;
                      return (
                        <button
                          key={item.key}
                          onClick={() => handleSubcategorySelect(item.key)}
                          className={`group flex w-full items-center justify-between rounded px-3 py-1.5 text-sm transition-all ${
                            isSubSelected
                              ? 'bg-(--palm)/10 text-(--palm) font-medium'
                              : 'text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)'
                          }`}
                        >
                          <span className="truncate">{item.label}</span>
                          {isSubSelected && <Check className="size-3.5 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Countries */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-(--sea-ink-soft)">
          Страна
        </h3>
        <div className="space-y-1">
          {/* ALL button for countries */}
          <button
            onClick={() => handleCountrySelect(undefined)}
            className={`group flex w-full items-center justify-between rounded px-3 py-2 text-sm transition-all ${
              !activeFilters.country
                ? 'bg-(--palm)/10 text-(--palm) font-medium'
                : 'text-(--sea-ink) hover:bg-(--link-bg-hover)'
            }`}
          >
            <span>Все</span>
            {!activeFilters.country && <Check className="size-3.5 shrink-0" />}
          </button>
          
          {filters.countries.map((country) => {
            const isSelected = activeFilters.country === country.key;
            return (
              <button
                key={country.key}
                onClick={() => handleCountrySelect(country.key)}
                className={`group flex w-full items-center justify-between rounded px-3 py-2 text-sm transition-all ${
                  isSelected
                    ? 'bg-(--palm)/10 text-(--palm) font-medium'
                    : 'text-(--sea-ink) hover:bg-(--link-bg-hover)'
                }`}
              >
                <span className="flex items-center gap-2">
                  {country.flag && <span className="text-base">{country.flag}</span>}
                  {country.name}
                </span>
                {isSelected && <Check className="size-3.5 shrink-0" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}