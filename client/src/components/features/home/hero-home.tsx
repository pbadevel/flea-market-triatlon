// src/components/features/home/hero-home.tsx
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Waves,
  Bike,
  Footprints,
  Watch,
  Medal,
  Snowflake,
  ChevronRight,
  // Heart,
  MapPin,
  Tag,
} from 'lucide-react'
import { adsQueryOptions, filtersQueryOptions } from '@/lib/queries/ads'
import type { LucideIcon } from 'lucide-react'

// Стили плиток категорий — подбираются по ключевым словам в label
const TILE_STYLES: { match: string[]; color: string; icon: LucideIcon }[] = [
  { match: ['плав', 'swim'], color: 'text-sky-600 bg-sky-50', icon: Waves },
  { match: ['велос', 'bike', 'cycl'], color: 'text-emerald-600 bg-emerald-50', icon: Bike },
  { match: ['бег', 'run'], color: 'text-orange-600 bg-orange-50', icon: Footprints },
  { match: ['час', 'электрон', 'watch', 'gps'], color: 'text-slate-600 bg-slate-100', icon: Watch },
  { match: ['медал', 'слот', 'finish', 'наград'], color: 'text-violet-600 bg-violet-50', icon: Medal },
  { match: ['лыж', 'ski', 'зим', 'снег'], color: 'text-indigo-600 bg-indigo-50', icon: Snowflake },
]
const TILE_FALLBACKS: { color: string; icon: LucideIcon }[] = [
  { color: 'text-sky-600 bg-sky-50', icon: Waves },
  { color: 'text-emerald-600 bg-emerald-50', icon: Bike },
  { color: 'text-orange-600 bg-orange-50', icon: Footprints },
  { color: 'text-slate-600 bg-slate-100', icon: Watch },
  { color: 'text-violet-600 bg-violet-50', icon: Medal },
  { color: 'text-indigo-600 bg-indigo-50', icon: Snowflake },
]

const tileStyleFor = (label: string, index: number) => {
  const low = label.toLowerCase()
  const found = TILE_STYLES.find((s) => s.match.some((m) => low.includes(m)))
  return found ?? TILE_FALLBACKS[index % TILE_FALLBACKS.length]
}

const condition_summary = (c: string | null | undefined): string => {
  const map: Record<string, string> = {
    new: 'Новое',
    like_new: 'Как нов.',
    used: 'Б/У',
  }
  return map[c ?? ''] ?? 'Б/У'
}

type Tile = {
  key: string
  label: string
  color: string
  icon: LucideIcon
  img?: string
}

export function HeroHome({
  onCategoryClick,
}: {
  onCategoryClick?: (key: string) => void
}) {
  const { data: filterConfig } = useQuery(filtersQueryOptions())
  const { data: adsData } = useQuery(
    adsQueryOptions({ page: 1, limit: 12, sort: 'created_at_desc' }),
  )
  // Значок лайка убран
  // const [liked, setLiked] = useState<Set<number>>(new Set())

  const tiles = useMemo<Tile[]>(() => {
    const cats: { key: string; label: string }[] =
      filterConfig?.categories ?? []
    const ads: any[] = adsData?.data ?? []
    return cats.slice(0, 6).map((c, i) => {
      const s = {
        ...(TILE_FALLBACKS[i % TILE_FALLBACKS.length] as {
          color: string
          icon: LucideIcon
        }),
        ...tileStyleFor(c.label, i),
      }
      // Первая попавшаяся фотка товара из этой категории — фон плитки
      const withCover = ads.find(
        (a) => a.category === c.key || a.subcategory === c.key,
      )
      const coverFromPhotos =
        withCover?.cover_url ??
        (Array.isArray(withCover?.photos) ? withCover.photos?.[0] : undefined)
      return {
        key: c.key,
        label: c.label,
        color: s.color,
        icon: s.icon,
        img: coverFromPhotos || undefined,
      }
    })
  }, [filterConfig, adsData])
  const freshAds = (adsData?.data ?? []).slice(0, 4)
  // const toggleLike = (id: number) =>
  //   setLiked((prev) => {
  //     const next = new Set(prev)
  //     next.has(id) ? next.delete(id) : next.add(id)
  //     return next
  //   })

  return (
    <div className="pb-2">
      {/* Плитки категорий */}
      <div className="page-wrap pt-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {tiles.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => {
                  onCategoryClick?.(t.key)
                  document
                    .getElementById('catalog')
                    ?.scrollIntoView({ behavior: 'smooth' })
                }}
                className="group relative aspect-[4/3] overflow-hidden rounded-2xl text-left border border-(--line) bg-(--surface-strong) transition hover:shadow-md sm:aspect-[16/10]"
              >
                {t.img && (
                  <img
                    src={t.img}
                    alt=""
                    loading="lazy"
                    className="absolute inset-0 h-full w-full object-cover transition duration-300 group-hover:scale-105"
                  />
                )}
                {t.img && (
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                )}
                <div
                  className="relative flex h-full flex-col justify-between p-3"
                >
                  <span
                    className={`flex size-9 items-center justify-center rounded-xl ${
                      t.img
                        ? 'bg-white/85 backdrop-blur-sm'
                        : t.color
                    }`}
                  >
                    <Icon className="size-5" strokeWidth={2} />
                  </span>
                  <span
                    className={`line-clamp-2 text-xs font-semibold leading-snug sm:text-[13px] ${
                      t.img ? 'text-white' : 'text-(--sea-ink)'
                    }`}
                  >
                    {t.label.replace(/\p{Extended_Pictographic}/gu, '').trim()}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Свежие объявления */}
      {freshAds.length > 0 && (
        <div className="page-wrap mt-7">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-extrabold tracking-tight text-(--sea-ink)">
              Свежие объявления
            </h2>
            <a
              href="#catalog"
              className="flex items-center gap-0.5 text-sm font-semibold text-(--palm) hover:underline"
            >
              Все объявления <ChevronRight className="size-4" />
            </a>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {freshAds.map((p: any) => (
              <div
                key={p.id}
                className="overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong) shadow-sm transition hover:shadow-md"
              >
                <div className="relative aspect-[16/10] overflow-hidden bg-(--surface) dark:bg-(--chip-bg)">
                  {p.cover_url ||
                  (Array.isArray(p.photos) && p.photos.length > 0) ? (
                    <img
                      src={p.cover_url ?? p.photos[0]}
                      alt={p.title}
                      loading="lazy"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="flex h-full w-full items-center justify-center text-(--sea-ink-soft)/40">
                      <Tag className="size-8" strokeWidth={1.5} />
                    </span>
                  )}
                  {/* Значок лайка убран */}
                  {/* <button
                    onClick={() => toggleLike(p.id)}
                    aria-label="В избранное"
                    className="absolute right-3 top-3 rounded-full bg-white/90 p-2 shadow-sm transition hover:scale-110"
                  >
                    <Heart
                      className={`size-5 ${liked.has(p.id) ? 'fill-red-500 text-red-500' : 'text-gray-400'}`}
                    />
                  </button> */}
                </div>
                <div className="p-4">
                  <div className="text-lg font-bold text-(--sea-ink)">
                    {Number(p.price ?? 0).toLocaleString('ru-RU')} ₽
                  </div>
                  <h3 className="mt-0.5 line-clamp-1 text-sm text-(--sea-ink)">
                    {p.title}
                  </h3>
                  <div className="mt-2 flex items-center justify-between text-xs text-(--sea-ink-soft)">
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3.5" /> {p.city ?? '—'}
                    </span>
                    <span>{condition_summary(p.condition)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
