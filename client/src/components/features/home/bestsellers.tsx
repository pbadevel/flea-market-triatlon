// src/components/features/home/bestsellers.tsx
import { Link } from '@tanstack/react-router'
import { ChevronLeft, ChevronRight, Filter, MapPin, Tag } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Filters } from './filters'
import { adsQueryOptions, filtersQueryOptions } from '@/lib/queries/ads'
import { AdFilters } from '@/types/ad'

// --- Компонент пагинации ---
function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}) {
  if (totalPages <= 1) return null

  const handlePageClick = (p: number) => {
    onPageChange(p)
    // Плавная прокрутка наверх при смене страницы
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const renderPageButton = (p: number) => (
    <button
      key={p}
      onClick={() => handlePageClick(p)}
      className={`min-w-[2.5rem] rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
        p === page
          ? 'bg-(--palm) border-(--palm) text-white'
          : 'border-(--line) bg-(--surface-strong) text-(--sea-ink) hover:bg-(--link-bg-hover)'
      }`}
    >
      {p}
    </button>
  )

  const renderEllipsis = (key: string) => (
    <span key={key} className="px-2 text-(--sea-ink-soft)">
      ...
    </span>
  )

  const pages: (number | string)[] = []
  const maxVisible = 5

  if (totalPages <= maxVisible) {
    for (let i = 1; i <= totalPages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (page > 3) pages.push('ellipsis-start')

    const start = Math.max(2, page - 1)
    const end = Math.min(totalPages - 1, page + 1)

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (page < totalPages - 2) pages.push('ellipsis-end')
    pages.push(totalPages)
  }

  return (
    <div className="flex items-center justify-center gap-1 mt-8 mb-4 flex-wrap">
      <button
        onClick={() => handlePageClick(Math.max(1, page - 1))}
        disabled={page <= 1}
        className="flex items-center gap-1 rounded-lg border border-(--line) bg-(--surface-strong) px-3 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="size-4" />
        <span className="hidden sm:inline">Назад</span>
      </button>

      {pages.map((p) =>
        typeof p === 'string' ? renderEllipsis(p) : renderPageButton(p),
      )}

      <button
        onClick={() => handlePageClick(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
        className="flex items-center gap-1 rounded-lg border border-(--line) bg-(--surface-strong) px-3 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <span className="hidden sm:inline">Вперед</span>
        <ChevronRight className="size-4" />
      </button>
    </div>
  )
}
// ---------------------------

export function Bestsellers({
  categoriesOverride,
}: { categoriesOverride?: string[] } = {}) {
  const [filters, setFilters] = useState<AdFilters>({
    page: 1,
    limit: 20,
    sort: 'created_at_desc',
  })

  // Синхронизация с плитками категорий на главной (HeroHome)
  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      categories: categoriesOverride?.length ? categoriesOverride : undefined,
      page: 1,
    }))
  }, [categoriesOverride])

  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false)

  const {
    data: adsData,
    isLoading,
    isError,
    error,
  } = useQuery(adsQueryOptions(filters))

  const { data: filterConfig } = useQuery(filtersQueryOptions())

  const totalPages = Math.ceil((adsData?.total || 0) / (filters.limit || 20))
  const ads = adsData?.data || []

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }))
  }

  const handleFilterChange = (newFilters: Partial<AdFilters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: 1, // Сброс на первую страницу при изменении фильтров
    }))
  }

  if (isError) {
    return (
      <div className="py-8 text-center text-red-500">
        Ошибка: {error?.message}
      </div>
    )
  }

  return (
    <section className="py-4">
      {/* Категории выбираются плитками на главной (HeroHome) — чипы убраны, чтобы не дублировать */}
      <div className="page-wrap">
        {/* Mobile Filter Header */}
        <div className="lg:hidden mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-(--sea-ink)">
            Товары {adsData?.total ? `(${adsData.total})` : ''}
          </h2>
          <button
            onClick={() => setIsMobileFilterOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-(--line) bg-(--surface-strong) px-3 py-1.5 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover)"
          >
            <Filter className="size-4" />
            Фильтры
            {(() => {
              const n =
                (filters.categories?.length ?? 0) +
                (filters.subcategories?.length ?? 0) +
                (filters.countries?.length ?? 0) +
                (filters.cities?.length ?? 0) +
                (filters.condition ? 1 : 0) +
                (filters.ad_type ? 1 : 0) +
                (filters.minPrice !== undefined ? 1 : 0) +
                (filters.maxPrice !== undefined ? 1 : 0)
              return n > 0 ? ` (${n})` : ''
            })()}
          </button>
        </div>

        <div className="flex gap-8">
          {/* Desktop Sidebar */}
          <aside className="w-64 shrink-0 hidden lg:block">
            {filterConfig ? (
              <Filters
                filters={filterConfig}
                activeFilters={filters}
                onFilterChange={handleFilterChange}
              />
            ) : (
              <div className="text-center py-8 text-(--sea-ink-soft)">
                Загрузка фильтров...
              </div>
            )}
          </aside>

          {/* Main Content */}
          <div className="flex-1">
            {/* Responsive Header with Page Info */}
            <div className="mb-4 hidden items-center justify-between lg:flex">
              <h2 className="text-lg font-semibold text-(--sea-ink)">
                Товары {adsData?.total ? `(${adsData.total})` : ''}
              </h2>
              {totalPages > 1 && (
                <div className="text-sm font-medium text-(--sea-ink-soft)">
                  Страница {filters.page || 1} из {totalPages}
                </div>
              )}
            </div>

            {isLoading ? (
              <div className="text-center py-8 text-(--sea-ink-soft)">
                Загрузка...
              </div>
            ) : ads.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-(--sea-ink-soft)">Товары не найдены</p>
                <button
                  onClick={() =>
                    setFilters({
                      page: 1,
                      limit: 20,
                      sort: filters.sort || 'created_at_desc',
                    })
                  }
                  className="mt-4 text-sm text-(--palm) hover:underline"
                >
                  Сбросить фильтры
                </button>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {ads.map((product) => (
                    <Link
                      key={product.id}
                      to="/product/$productId"
                      params={{ productId: String(product.id) }}
                      className="group overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong) transition hover:shadow-md"
                    >
                      <div className="relative aspect-[4/3] overflow-hidden bg-(--surface) dark:bg-(--chip-bg)">
                        {product.discount && (
                          <span className="absolute left-2 top-2 rounded-full bg-red-500 px-1.5 py-0.5 text-[9px] font-semibold text-white">
                            -{product.discount}%
                          </span>
                        )}
                        {product.cover_url ||
                        (Array.isArray(product.photos) &&
                          product.photos.length > 0) ? (
                          <img
                            src={product.cover_url ?? product.photos[0]}
                            alt={product.title}
                            loading="lazy"
                            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                          />
                        ) : (
                          <span className="flex h-full w-full items-center justify-center text-(--sea-ink-soft)/40">
                            <Tag className="size-7" strokeWidth={1.5} />
                          </span>
                        )}
                      </div>
                      <div className="p-2.5">
                        <span className="text-sm font-bold text-(--sea-ink)">
                          {Number(product.price ?? 0).toLocaleString('ru-RU')} ₽
                        </span>
                        {product.old_price && (
                          <span className="ml-1 text-[10px] text-(--sea-ink-soft) line-through">
                            {Number(product.old_price).toLocaleString('ru-RU')} ₽
                          </span>
                        )}
                        <h3 className="mt-0.5 line-clamp-1 text-xs text-(--sea-ink)">
                          {product.title}
                        </h3>
                        <div className="mt-1.5 flex items-center justify-between text-[11px] text-(--sea-ink-soft)">
                          <span className="flex items-center gap-1">
                            <MapPin className="size-3.5" /> {product.city || '—'}
                          </span>
                          <span>
                            {product.condition === 'new'
                              ? 'Новое'
                              : product.condition === 'like_new'
                                ? 'Как нов.'
                                : 'Б/У'}
                          </span>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>

                {/* Полноценная пагинация внизу списка (видна на всех устройствах) */}
                <Pagination
                  page={filters.page || 1}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Filter Modal */}
      {isMobileFilterOpen && filterConfig && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setIsMobileFilterOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-full bg-(--surface-strong) shadow-xl lg:hidden">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-(--line) px-4 py-3">
                <h3 className="text-base font-semibold text-(--sea-ink)">
                  Фильтры
                </h3>
                <button
                  onClick={() => setIsMobileFilterOpen(false)}
                  className="rounded p-1 text-(--sea-ink-soft) hover:bg-(--link-bg-hover)"
                >
                  ✕
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <Filters
                  filters={filterConfig}
                  activeFilters={filters}
                  onFilterChange={handleFilterChange}
                />
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
