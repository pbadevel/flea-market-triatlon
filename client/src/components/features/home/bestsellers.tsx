// src/components/features/home/bestsellers.tsx
import { Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Filters } from "./filters";
import { useCountry } from "@/contexts/CountryContext";
import { adsQueryOptions, filtersQueryOptions } from "@/lib/queries/ads";
import { AdFilters } from "@/types/ad";

export function Bestsellers() {
  // const { country } = useCountry();
  const [filters, setFilters] = useState<AdFilters>({
    page: 1,
    limit: 20,
    country: undefined,
    sort: 'created_at_desc',
  });
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);

  const { data: adsData, isLoading, isError, error } = useQuery(
    adsQueryOptions(filters)
  );

  const { data: filterConfig } = useQuery(filtersQueryOptions());


  const totalPages = Math.ceil((adsData?.total || 0) / (filters.limit || 20));
  const ads = adsData?.data || [];

  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  const handleFilterChange = (newFilters: Partial<AdFilters>) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
      page: 1,
    }));
  };

  const handleMobileFilterApply = () => {
    setIsMobileFilterOpen(false);
    handlePageChange(1);
  };

  if (isError) {
    return (
      <div className="py-8 text-center text-red-500">
        Ошибка: {error?.message}
      </div>
    );
  }

  return (
    <section className="py-8">
      <div className="page-wrap">
        {/* Mobile Filter Header */}
        <div className="lg:hidden mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-(--sea-ink)">
            Товары {adsData?.total ? `(${adsData.total})` : ''}
          </h2>
          <button
            onClick={() => setIsMobileFilterOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-(--line) bg-white px-3 py-1.5 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover)"
          >
            <Filter className="size-4" />
            Фильтры{filters && Object.values(filters).some(v => v) && ` (${Object.values(filters).filter(v => v).length})`}
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
            {/* Header with pagination */}
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-(--sea-ink)">
                Товары {adsData?.total ? `(${adsData.total})` : ''}
              </h2>
              <div className="flex gap-1">
                <div className="flex rounded p-1.5 text-(--sea-ink-soft)">
                  {filters.page || 1}/{totalPages || 1}
                </div>
                <button
                  onClick={() => handlePageChange(Math.max(1, (filters.page || 1) - 1))}
                  disabled={!filters.page || filters.page <= 1}
                  className="rounded p-1.5 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) disabled:opacity-30"
                >
                  <ChevronLeft className="size-4" />
                </button>
                <button
                  onClick={() => handlePageChange(Math.min(totalPages, (filters.page || 1) + 1))}
                  disabled={!totalPages || (filters.page || 1) >= totalPages}
                  className="rounded p-1.5 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) disabled:opacity-30"
                >
                  <ChevronRight className="size-4" />
                </button>
              </div>
            </div>

            {/* Products Grid */}
            {isLoading ? (
              <div className="text-center py-8 text-(--sea-ink-soft)">Загрузка...</div>
            ) : ads.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-(--sea-ink-soft)">Товары не найдены</p>
                <button
                  onClick={() => setFilters({ page: 1, limit: 20 })}
                  className="mt-4 text-sm text-(--palm) hover:underline"
                >
                  Сбросить фильтры
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-3">
                {ads.map((product) => (
                  <Link
                    key={product.id}
                    to="/product/$productId"
                    params={{ productId: String(product.id) }}
                    className="group rounded-lg border border-(--line) bg-white p-2 hover:bg-(--foam)"
                  >
                    <div className="relative mb-2 aspect-square overflow-hidden rounded bg-gray-50">
                      {product.discount && (
                        <span className="absolute left-1.5 top-1.5 rounded bg-red-500 px-1 py-0.5 text-[9px] font-semibold text-white">
                          -{product.discount}%
                        </span>
                      )}
                      <img
                        src={product.cover_url}
                        alt={product.title}
                        className="h-full w-full object-cover transition group-hover:scale-105"
                      />
                    </div>
                    <h3 className="line-clamp-2 text-[11px] font-medium text-(--sea-ink) leading-tight">
                      {product.title}
                    </h3>
                    <div className="mt-1 flex items-baseline gap-1">
                      <span className="text-xs font-semibold text-(--sea-ink)">
                        {product.price.toLocaleString()} ₽
                      </span>
                      {product.old_price && (
                        <span className="text-[10px] text-(--sea-ink-soft) line-through">
                          {product.old_price.toLocaleString()} ₽
                        </span>
                      )}
                    </div>
                    {/* Meta */}
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-(--sea-ink-soft)">
                      {product.city && <span>{product.city}</span>}
                      {product.condition && (
                        <span className="rounded bg-gray-100 px-1 py-0.5">
                          {product.condition === 'new' ? 'Новое' :
                          product.condition === 'used' ? 'Б/У' : 'Не указано'}
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
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
          <div className="fixed inset-y-0 left-0 z-50 w-80 max-w-full bg-white shadow-xl lg:hidden">
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-(--line) px-4 py-3">
                <h3 className="text-base font-semibold text-(--sea-ink)">Фильтры</h3>
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
              <div className="border-t border-(--line) p-4">
                <button
                  onClick={handleMobileFilterApply}
                  className="w-full rounded-lg bg-(--palm) py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90"
                >
                  Показать результаты
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}