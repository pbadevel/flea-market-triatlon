import { Link } from "@tanstack/react-router";
import { Ad } from "@/types/ad";

interface SearchMenuProps {
  query: string;
  results: Ad[];
  isLoading: boolean;
  onClose: () => void;
}

export function SearchMenu({ query, results, isLoading, onClose }: SearchMenuProps) {
  if (query.length < 2) {
    return (
      <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-(--line) bg-white p-3 shadow-lg z-50">
        <p className="text-sm text-(--sea-ink-soft)">Введите минимум 2 символа для поиска</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-(--line) bg-white p-4 shadow-lg z-50">
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-(--palm) border-t-transparent" />
          <span className="ml-2 text-sm text-(--sea-ink-soft)">Поиск...</span>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="absolute top-full left-0 right-0 mt-1 rounded-lg border border-(--line) bg-white p-4 shadow-lg z-50">
        <p className="text-sm text-(--sea-ink-soft)">Ничего не найдено по запросу "{query}"</p>
      </div>
    );
  }

  return (
    <div className="absolute top-full left-0 right-0 mt-1 max-h-96 overflow-auto rounded-lg border border-(--line) bg-white shadow-lg z-50">
      <div className="p-2">
        {results.map((item) => (
          <Link
            key={item.id}
            to={`/product/${item.id}`}
            onClick={onClose}
            className="flex items-center gap-3 rounded p-2 hover:bg-(--link-bg-hover) group"
          >
            <div className="size-12 shrink-0 overflow-hidden rounded bg-gray-50">
              <img
                src={item.cover_url || "/placeholder.jpg"}
                alt={item.title}
                className="h-full w-full object-cover"
              />
            </div>
            
            <div className="flex-1 min-w-0">
              <h4 className="truncate text-sm font-medium text-(--sea-ink) group-hover:text-(--palm)">
                {item.title}
              </h4>
              <div className="mt-0.5 flex items-baseline gap-1">
                <span className="text-xs font-semibold text-(--sea-ink)">
                  {item.price.toLocaleString()} ₽
                </span>
                {item.old_price && (
                  <span className="text-[10px] text-(--sea-ink-soft) line-through">
                    {item.old_price.toLocaleString()} ₽
                  </span>
                )}
              </div>
            </div>

            {item.discount && (
              <span className="shrink-0 rounded bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                -{item.discount}%
              </span>
            )}
          </Link>
        ))}
        
        
      </div>
    </div>
  );
}