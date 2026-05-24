// src/components/features/home/country-filter.tsx
import { type Country, countries } from "@/contexts/CountryContext";

interface CountryFilterProps {
  selectedCountry: Country | undefined;
  onCountryChange: (country: Country | undefined) => void;
}

// Список стран без 'all' - он обрабатывается отдельно
const countryList: Country[] = ['ru', 'kz', 'kg'];

export function CountryFilter({ selectedCountry, onCountryChange }: CountryFilterProps) {
  return (
    <div className="space-y-1">
      <div className="mb-3 text-xs font-semibold uppercase text-gray-500">
        Смотреть товары в стране
      </div>
      
      {/* Кнопка "ВСЕ" - передаёт undefined для сброса фильтра */}
      <button
        onClick={() => onCountryChange(undefined)}
        className={`flex w-full items-center justify-between rounded px-3 py-2 text-sm transition ${
          !selectedCountry || selectedCountry === 'all'
            ? 'bg-gray-200 font-medium text-gray-900'
            : 'text-gray-600 hover:bg-gray-100'
        }`}
      >
        <span>Все</span>
        {(!selectedCountry || selectedCountry === 'all') && (
          <svg className="size-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </button>
      
      {/* Остальные страны */}
      {countryList.map((code) => (
        <button
          key={code}
          suppressHydrationWarning={true}
          onClick={() => onCountryChange(code)}
          className={`flex w-full items-center justify-between rounded px-3 py-2 text-sm transition ${
            selectedCountry === code
              ? 'bg-gray-200 font-medium text-gray-900'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          <div className="flex items-center gap-2">
            {countries[code].flag && (
              <span className="text-lg">{countries[code].flag}</span>
            )}
            <span>{countries[code].name}</span>
          </div>
          {countries[code].count !== undefined && (
            <span className="text-xs text-gray-400">
              {countries[code].count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}