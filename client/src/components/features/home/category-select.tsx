// src/components/features/category-select.tsx
import { useState, useMemo } from 'react'
import { ChevronDown } from 'lucide-react'
import type { CategoryFilter, CategoryItem } from '@/types/ad'

interface CategorySelectProps {
  categories: CategoryFilter[]
  selectedCategory: string
  selectedSubcategory: string
  onCategoryChange: (value: string) => void
  onSubcategoryChange: (value: string) => void
}

export function CategorySelect({
  categories,
  selectedCategory,
  selectedSubcategory,
  onCategoryChange,
  onSubcategoryChange,
}: CategorySelectProps) {
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false)
  const [showSubcategoryDropdown, setShowSubcategoryDropdown] = useState(false)

  // Текущая выбранная категория
  const currentCategory = categories.find((c) => c.key === selectedCategory)

  // Все доступные подкатегории для выбранной категории
  const availableSubcategories = useMemo(() => {
    if (!currentCategory) return []
    
    const items: { group?: string; item: CategoryItem }[] = []
    
    // Группы (для bike)
    if (currentCategory.groups) {
      currentCategory.groups.forEach((group) => {
        group.items.forEach((item) => {
          items.push({ group: group.name, item })
        })
      })
    }
    
    // Простые items
    if (currentCategory.items) {
      currentCategory.items.forEach((item) => {
        items.push({ item })
      })
    }
    
    return items
  }, [currentCategory])

  const handleCategorySelect = (key: string) => {
    onCategoryChange(key)
    onSubcategoryChange('') // Сбрасываем подкатегорию
    setShowCategoryDropdown(false)
  }

  const handleSubcategorySelect = (key: string) => {
    onSubcategoryChange(key)
    setShowSubcategoryDropdown(false)
  }

  return (
    <div className="space-y-3">
      {/* Категория */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-(--sea-ink)">
          Категория *
        </label>
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowCategoryDropdown(!showCategoryDropdown)
              setShowSubcategoryDropdown(false)
            }}
            className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
          >
            <span className={selectedCategory ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
              {currentCategory?.label || 'Выберите категорию'}
            </span>
            <ChevronDown className="size-4 text-(--sea-ink-soft)" />
          </button>

          {showCategoryDropdown && (
            <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
              {categories.map((cat) => (
                <button
                  key={cat.key}
                  type="button"
                  onClick={() => handleCategorySelect(cat.key)}
                  className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                    selectedCategory === cat.key
                      ? 'bg-(--palm)/10 text-(--palm) font-medium'
                      : 'text-(--sea-ink)'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Подкатегория (показывается только если выбрана категория) */}
      {selectedCategory && availableSubcategories.length > 0 && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-(--sea-ink)">
            Подкатегория
          </label>
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setShowSubcategoryDropdown(!showSubcategoryDropdown)
                setShowCategoryDropdown(false)
              }}
              className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
            >
              <span className={selectedSubcategory ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                {selectedSubcategory
                  ? availableSubcategories.find((s) => s.item.key === selectedSubcategory)?.item.label || 'Выберите подкатегорию'
                  : 'Выберите подкатегорию (необязательно)'}
              </span>
              <ChevronDown className="size-4 text-(--sea-ink-soft)" />
            </button>

            {showSubcategoryDropdown && (
              <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                {availableSubcategories.map(({ group, item }, idx) => (
                  <div key={idx}>
                    {group && idx === 0 || (group && availableSubcategories[idx - 1].group !== group) ? (
                      <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50">
                        {group}
                      </div>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => handleSubcategorySelect(item.key)}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                        selectedSubcategory === item.key
                          ? 'bg-(--palm)/10 text-(--palm) font-medium'
                          : 'text-(--sea-ink)'
                      }`}
                    >
                      {item.label}
                      {item.requires_size && (
                        <span className="ml-2 text-xs text-(--sea-ink-soft)">(нужен размер)</span>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}