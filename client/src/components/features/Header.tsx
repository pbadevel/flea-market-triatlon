import { useState, useRef, useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { Search, Heart, User, X, Plus, BoxIcon, Bell, Shield } from "lucide-react";
import { SearchMenu } from "./search-menu";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adsQueryOptions } from "@/lib/queries/ads";
import { verifySession } from "@/lib/session";
import { fetchUnreadCount, fetchNotifications, markAllRead } from "@/lib/api/client/notifications";

export default function Header() {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const searchRef = useRef<HTMLDivElement>(null);

  const { data: session } = useQuery({
    queryKey: ['session'],
    queryFn: verifySession,
    staleTime: 0,
  });

  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  const { data: searchData, isLoading } = useQuery(
    adsQueryOptions(
      { search: debouncedQuery.length >= 2 ? debouncedQuery : undefined, limit: 10 },
    )
  );

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
    <header className="sticky top-0 z-40 bg-(--header-bg) backdrop-blur-xl border-b border-(--line)">
      <div className="page-wrap">
        <div className="flex h-14 items-center gap-3 justify-center">
          <Link to="/" className="shrink-0">
            <img src="/image.png" alt="TBSALE" className="h-10 w-auto rounded-lg" />
          </Link>

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
              className="w-full rounded-xl border border-(--line) bg-(--chip-bg) py-2 pl-8 pr-8 text-sm text-(--sea-ink) placeholder:text-(--sea-ink-soft) focus:border-(--palm) focus:outline-none"
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

          <div className="flex items-center gap-0.5">
            {session?.token && (
              <NotificationsBell token={session.token} />
            )}
            {session?.isAdmin && (
              <Link 
                to="/admin"
                className="rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--palm)" aria-label="Админ">
                <Shield className="size-4.5" />
              </Link>
            )}
            <Link 
              to={"/profile"}
              className="rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Профиль">
              <User className="size-4.5" />
            </Link>
            <Link 
              to={"/my-ads"}
              className="rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Мои объявления">
              <BoxIcon className="size-4.5" />
            </Link>
            <Link 
              to={"/create-ad"}
              className="rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Создать">
              <Plus className="size-4.5" />
            </Link>
            <button className="rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)" aria-label="Избранное">
              <Heart className="size-4.5" />
            </button>
          </div>
        </div>
      </div>

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

function NotificationsBell({ token }: { token: string }) {
  const [open, setOpen] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: unreadData } = useQuery({
    queryKey: ['unread-notifications'],
    queryFn: () => fetchUnreadCount(token),
    refetchInterval: 30000,
  });

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => fetchNotifications(token),
    enabled: open,
  });

  const markReadMut = useMutation({
    mutationFn: () => markAllRead(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unread-notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const count = (unreadData as any)?.count || 0;

  const [dropdownPos, setDropdownPos] = useState({ top: 0, right: 0 });

  const handleToggle = () => {
    const next = !open;
    if (!next) {
      setOpen(false);
      return;
    }
    const btn = bellRef.current?.querySelector('button');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      const dropdownWidth = Math.min(320, window.innerWidth - 32);
      const rightPos = Math.max(16, window.innerWidth - rect.right);
      setDropdownPos({
        top: rect.bottom + 8,
        right: Math.min(rightPos, window.innerWidth - dropdownWidth - 16),
      });
    }
    setOpen(true);
    if (count > 0) {
      markReadMut.mutate();
    }
  };

  return (
    <div ref={bellRef} className="relative">
      <button
        onClick={handleToggle}
        className="relative rounded-xl p-2 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
        aria-label="Уведомления"
      >
        <Bell className="size-4.5" />
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-[90]" onClick={() => setOpen(false)} />
          <div
            className="fixed z-[100] max-w-80 max-h-[60vh] overflow-y-auto rounded-2xl border border-(--line) bg-(--surface-strong) shadow-2xl"
            style={{
              top: dropdownPos.top,
              right: dropdownPos.right,
              width: `min(320px, calc(100vw - 32px))`,
            }}
          >
          <div className="flex items-center justify-between px-4 py-3 border-b border-(--line)">
            <h3 className="font-bold text-sm text-(--sea-ink)">Уведомления</h3>
            {count > 0 && (
              <button
                onClick={() => markReadMut.mutate()}
                className="text-xs text-(--palm) hover:underline"
              >
                Прочитать всё
              </button>
            )}
          </div>
          {(!notifications || (notifications as any[]).length === 0) ? (
            <div className="px-4 py-8 text-center text-sm text-(--sea-ink-soft)">
              Нет уведомлений
            </div>
          ) : (
            <div className="divide-y divide-(--line)">
              {(notifications as any[]).map((n: any) => (
                <div key={n.id} className={`px-4 py-3 ${!n.is_read ? 'bg-(--palm)/5' : ''}`}>
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5">
                      {n.type === 'success' ? (
                        <div className="w-2 h-2 rounded-full bg-green-500" />
                      ) : n.type === 'error' ? (
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-(--sea-ink)">{n.title}</p>
                      <p className="text-xs text-(--sea-ink-soft) mt-0.5 line-clamp-2">{n.message}</p>
                      <p className="text-xs text-(--sea-ink-soft) mt-1">
                        {new Date(n.created_at).toLocaleString('ru-RU')}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          </div>
        </>
      )}
    </div>
  );
}
