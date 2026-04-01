// src/components/features/home/header.tsx
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Search,
  Phone,
  Menu,
} from "lucide-react";
import ThemeToggle from "@/components/features/ThemeToggle";
import { CatalogMenu } from "./catalog-menu";
import { SearchMenu } from "./search-menu";
import { useMobileCatalog } from "./mobile-catalog-provider";


export default function Header() {
  const { open: openMobileCatalog } = useMobileCatalog();
  const [isCatalogOpen, setIsCatalogOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg) backdrop-blur-lg">
      <div className="page-wrap">
        {/* Main row */}
        <div className="flex h-16 items-center gap-6">
          {/* Logo */}
          <Link to="/" className="shrink-0">
            <div className="flex items-baseline gap-1">
              <span className="text-xl font-bold text-(--sea-ink)">TB</span>
              <span className="text-xl font-light text-(--accent)">SALE</span>
            </div>
          </Link>

          {/* Catalog - Desktop */}
          <div className="relative hidden lg:block">
            <button
              onClick={() => {
                setIsCatalogOpen(!isCatalogOpen);
                setIsSearchOpen(false);
              }}
              className="flex items-center gap-2 rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--sea-ink) transition hover:bg-(--link-bg-hover)"
              aria-label="Каталог"
              aria-expanded={isCatalogOpen}
            >
              <Menu className="size-4" />
              Каталог
            </button>
            {isCatalogOpen && <CatalogMenu />}
          </div>

          {/* Search */}
          <div className="relative flex-1 max-w-2xl">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-(--sea-ink-soft)" />
              <input
                type="search"
                placeholder="Поиск по товарам..."
                onFocus={() => {
                  setIsSearchOpen(true);
                  setIsCatalogOpen(false);
                }}
                onBlur={() => setTimeout(() => setIsSearchOpen(false), 200)}
                className="w-full rounded-lg border border-(--line) bg-(--chip-bg) py-2 pl-10 pr-4 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--accent) focus:outline-none"
              />
            </div>
            {isSearchOpen && <SearchMenu />}
          </div>

          {/* Phone - hidden on mobile */}
          <div className="hidden flex-col items-end lg:flex">
            <a
              href="tel:+79995738585"
              className="text-sm font-semibold text-(--sea-ink)"
            >
              +7 (999) 573-85-85
            </a>
            <button className="text-xs text-(--sea-ink-soft) hover:text-(--accent)">
              Обратный звонок
            </button>
          </div>

          {/* Actions - hidden on mobile (shown in tabbar) */}
          <div className="ml-auto hidden items-center gap-1 lg:flex">
            <button
              className="rounded-lg p-2 text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
              aria-label="Профиль"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </button>
            <button
              className="rounded-lg p-2 text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
              aria-label="Сравнение"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
              </svg>
            </button>
            <button
              className="rounded-lg p-2 text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
              aria-label="Избранное"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </button>
            <button
              className="rounded-lg p-2 text-(--sea-ink-soft) transition hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
              aria-label="Корзина"
            >
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            </button>
            <div className="ml-2 pl-2 border-l border-(--line)">
              <ThemeToggle />
            </div>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={openMobileCatalog}
            className="rounded-lg p-2 text-(--sea-ink) lg:hidden"
            aria-label="Меню"
          >
            <Menu className="size-5" />
          </button>
        </div>

        {/* Categories - hidden on mobile */}
        <nav className="hidden items-center gap-6 overflow-x-auto py-3 text-sm lg:flex">
          <Link
            to="/"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Распродажа
          </Link>
          <Link
            to="/smartwatches"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Смарт-часы
          </Link>
          <Link
            to="/fishfinders"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Эхолоты
          </Link>
          <Link
            to="/navigators"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Навигаторы
          </Link>
          <Link
            to="/accessories"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Аксессуары
          </Link>
          <Link
            to="/bike"
            className="whitespace-nowrap font-medium text-(--sea-ink-soft) transition hover:text-(--sea-ink)"
            activeProps={{ className: "text-(--sea-ink)" }}
          >
            Велоэлектроника
          </Link>
        </nav>
      </div>

      {/* Click outside to close desktop menus */}
      {(isCatalogOpen || isSearchOpen) && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => {
            setIsCatalogOpen(false);
            setIsSearchOpen(false);
          }}
        />
      )}
    </header>
  );
}