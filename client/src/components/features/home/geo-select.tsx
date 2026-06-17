// src/components/features/geo-select.tsx
import { useState, useMemo } from 'react'
import { ChevronDown, MapPin, Plus } from 'lucide-react'
import type { GeoCountry } from '@/types/ad'

interface GeoSelectProps {
  countries: GeoCountry[]
  defaultCities: string[]
  selectedCountry: string
  selectedCity: string
  onCountryChange: (value: string) => void
  onCityChange: (value: string) => void
}

export function GeoSelect({
  countries,
  defaultCities,
  selectedCountry,
  selectedCity,
  onCountryChange,
  onCityChange,
}: GeoSelectProps) {
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [showCityDropdown, setShowCityDropdown] = useState(false)
  const [customCity, setCustomCity] = useState('')
  const [useCustomCity, setUseCustomCity] = useState(false)

  // Текущая выбранная страна
  const currentCountry = countries.find((c) => c.key === selectedCountry)

  // Города для отображения: города выбранной страны + defaultCities
  const availableCities = useMemo(() => {
    const cities = new Set<string>()
    
    // Сначала добавляем defaultCities (Москва, Питер, Сочи...)
    defaultCities.forEach((city) => cities.add(city))
    
    // Потом добавляем города выбранной страны
    if (currentCountry) {
      currentCountry.cities.forEach((city) => cities.add(city))
    }
    
    return Array.from(cities).sort((a, b) => a.localeCompare(b, 'ru'))
  }, [currentCountry, defaultCities])

  const handleCountrySelect = (key: string) => {
    onCountryChange(key)
    onCityChange('') // Сбрасываем город
    setUseCustomCity(false)
    setCustomCity('')
    setShowCountryDropdown(false)
  }

  const handleCitySelect = (city: string) => {
    onCityChange(city)
    setUseCustomCity(false)
    setCustomCity('')
    setShowCityDropdown(false)
  }

  const handleCustomCitySubmit = () => {
    if (customCity.trim()) {
      onCityChange(customCity.trim())
      setUseCustomCity(false)
      setCustomCity('')
      setShowCityDropdown(false)
    }
  }

  return (
    <div className="space-y-3">
      {/* Страна */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-(--sea-ink)">
          Страна
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowCountryDropdown(!showCountryDropdown)
              setShowCityDropdown(false)
            }}
            className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
          >
            <span className={selectedCountry ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
              {currentCountry ? `${currentCountry.flag} ${currentCountry.name}` : 'Выберите страну (необязательно)'}
            </span>
            <ChevronDown className="size-4 text-(--sea-ink-soft)" />
          </button>

          {showCountryDropdown && (
            <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
              <button
                type="button"
                onClick={() => {
                  onCountryChange('')
                  onCityChange('')
                  setShowCountryDropdown(false)
                }}
                className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                  !selectedCountry
                    ? 'bg-(--palm)/10 text-(--palm) font-medium'
                    : 'text-(--sea-ink)'
                }`}
              >
                Не указана
              </button>
              {countries.map((country) => (
                <button
                  key={country.key}
                  type="button"
                  onClick={() => handleCountrySelect(country.key)}
                  className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                    selectedCountry === country.key
                      ? 'bg-(--palm)/10 text-(--palm) font-medium'
                      : 'text-(--sea-ink)'
                  }`}
                >
                  {country.flag} {country.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Город */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-(--sea-ink)">
          Город *
        </label>
        
        {useCustomCity ? (
          // Ручной ввод города
          <div className="flex gap-2">
            <input
              type="text"
              value={customCity}
              onChange={(e) => setCustomCity(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCustomCitySubmit()}
              placeholder="Введите город"
              className="flex-1 rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
              autoFocus
            />
            <button
              type="button"
              onClick={handleCustomCitySubmit}
              className="rounded-lg bg-(--palm) px-4 py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90"
            >
              OK
            </button>
            <button
              type="button"
              onClick={() => {
                setUseCustomCity(false)
                setCustomCity('')
              }}
              className="rounded-lg border border-(--line) px-3 py-2.5 text-(--sea-ink-soft) hover:bg-(--link-bg-hover)"
            >
              ✕
            </button>
          </div>
        ) : (
          // Выбор из списка
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setShowCityDropdown(!showCityDropdown)
                setShowCountryDropdown(false)
              }}
              className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
            >
              <div className="flex items-center gap-2">
                <MapPin className="size-4 text-(--sea-ink-soft)" />
                <span className={selectedCity ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                  {selectedCity || 'Выберите город'}
                </span>
              </div>
              <ChevronDown className="size-4 text-(--sea-ink-soft)" />
            </button>

            {showCityDropdown && (
              <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                {/* Популярные города */}
                {defaultCities.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50 sticky top-0">
                      Популярные города
                    </div>
                    {defaultCities.map((city) => (
                      <button
                        key={city}
                        type="button"
                        onClick={() => handleCitySelect(city)}
                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                          selectedCity === city
                            ? 'bg-(--palm)/10 text-(--palm) font-medium'
                            : 'text-(--sea-ink)'
                        }`}
                      >
                        {city}
                      </button>
                    ))}
                  </div>
                )}

                {/* Города выбранной страны */}
                {currentCountry && currentCountry.cities.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50 sticky top-0">
                      {currentCountry.flag} {currentCountry.name}
                    </div>
                    {currentCountry.cities
                      .filter((city) => !defaultCities.includes(city))
                      .map((city) => (
                        <button
                          key={city}
                          type="button"
                          onClick={() => handleCitySelect(city)}
                          className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                            selectedCity === city
                              ? 'bg-(--palm)/10 text-(--palm) font-medium'
                              : 'text-(--sea-ink)'
                          }`}
                        >
                          {city}
                        </button>
                      ))}
                  </div>
                )}

                {/* Кнопка "Другой город" */}
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomCity(true)
                    setShowCityDropdown(false)
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-(--palm) hover:bg-(--link-bg-hover) transition border-t border-(--line)"
                >
                  <Plus className="size-4" />
                  Ввести город вручную
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}