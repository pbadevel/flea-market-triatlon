import { useState, useRef, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { Search, ShoppingCart, Heart, User, X, Plus, BoxIcon } from "lucide-react";
import { SearchMenu } from "./search-menu";
import { useQuery } from "@tanstack/react-query";
import { adsQueryOptions } from "@/lib/queries/ads";



export default function Header() {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchRef = useRef<HTMLDivElement>(null);

  // Поиск с debounce
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Загрузка результатов поиска с правильным enabled
  const { data: searchData, isLoading } = useQuery(
    adsQueryOptions(
      { search: debouncedQuery.length >= 2 ? debouncedQuery : undefined, limit: 10 },
    )
  );
  


  // Закрытие поиска при клике вне
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
        setIsFocused(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Сброс поиска при закрытии
  useEffect(() => {
    if (!isSearchOpen) {
      setSearchQuery("");
    }
  }, [isSearchOpen]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    if (e.target.value.length > 0 && !isSearchOpen) {
      setIsSearchOpen(true);
    }
  };

  const handleClear = () => {
    setSearchQuery("");
    setIsSearchOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
      <div className="page-wrap">
        <div className="flex h-14 items-center gap-3 justify-center">
          {/* Logo */}
          <Link to="/" className="shrink-0">
            <span className="text-lg font-bold text-(--sea-ink)">TB</span>
            <span className="text-lg font-semibold text-(--palm)">SALE</span>
          </Link>

          {/* Search */}
          <div ref={searchRef} className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-(--sea-ink-soft)" />
            
            <input
              type="search"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => {
                setIsFocused(true);
                if (searchQuery.length > 0) setIsSearchOpen(true);
              }}
              placeholder="Поиск товаров..."
              className="w-full rounded border border-(--line) bg-(--chip-bg) py-1.5 pl-8 pr-8 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
            />
            
            {(searchQuery || isFocused) && (
              <button
                onClick={handleClear}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-(--sea-ink-soft) hover:text-(--sea-ink)"
                aria-label="Очистить поиск"
              >
                <X className="size-4" />
              </button>
            )}

            {isSearchOpen && (
              <SearchMenu
                query={debouncedQuery}
                results={searchData?.data || []}
                isLoading={isLoading}
                onClose={() => setIsSearchOpen(false)}
              />
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-0.5">
            <Link 
              to={"/profile"}
              className="rounded p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Профиль">
              
              <User className="size-4.5" />
            
            </Link>
            <Link 
              to={"/my-ads"}
              className="rounded p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Профиль">
              
              <BoxIcon className="size-4.5" />
            
            </Link>
            <Link 
              to={"/create-ad"}
              className="rounded p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Профиль">
              
              <Plus className="size-4.5" />
            
            </Link>
            <button className="rounded p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Избранное">
              <Heart className="size-4.5" />
            </button>
            <div className="hidden sm:block ml-0.5">
              {/* <ThemeToggle /> */}
            </div>
          </div>
        </div>
      </div>

      {/* Overlay */}
      {isSearchOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => {
            setIsSearchOpen(false);
            setIsFocused(false);
          }}
        />
      )}
    </header>
  );
}