// src/components/features/product-detail.tsx
import { useParams } from '@tanstack/react-router'
import { ArrowLeft, Heart, Share2, ShoppingCart } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { productQueryOptions } from '@/lib/queries/ads'


export function ProductDetail() {
  const { productId } = useParams({ from: '/product/$productId' })

  const { data: product, isLoading, isError, error } = useQuery(
    productQueryOptions(productId)
  )

  console.log(product)
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center text-(--sea-ink-soft)">Загрузка...</div>
      </div>
    )
  }

  if (isError || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Товар не найден
          </h1>
          <p className="text-(--sea-ink-soft) mb-6">
            {error instanceof Error ? error.message : 'Произошла ошибка'}
          </p>
          <Link 
            to="/" 
            className="inline-flex items-center gap-2 text-(--palm) hover:underline"
          >
            <ArrowLeft className="size-4" />
            Вернуться на главную
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-(--bg)">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-(--line) bg-(--header-bg)">
        <div className="page-wrap">
          <div className="flex h-14 items-center gap-3">
            <Link 
              to="/" 
              className="flex items-center gap-1 text-(--sea-ink-soft) hover:text-(--sea-ink)"
            >
              <ArrowLeft className="size-5" />
              <span className="text-sm">Назад</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Product Content */}
      <div className="page-wrap py-8">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Image Gallery */}
          <div className="space-y-4">
            <div className="aspect-square overflow-hidden rounded-lg bg-gray-50">
              <img
                src={product.cover_url}
                alt={product.title}
                className="h-full w-full object-cover"
              />
            </div>
            {/* Thumbnails if multiple photos */}
            {product.photos && product.photos.length > 1 && (
              <div className="flex gap-2 overflow-x-auto">
                {product.photos.map((photo, index) => (
                  <button
                    key={index}
                    className="shrink-0 aspect-square w-16 overflow-hidden rounded border border-(--line) hover:border-(--palm)"
                  >
                    <img
                      src={photo}
                      alt={`${product.title} ${index + 1}`}
                      className="h-full w-full object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="space-y-6">
            {/* Title & Price */}
            <div>
              <h1 className="text-2xl font-bold text-(--sea-ink) mb-2">
                {product.title}
              </h1>
              
              <div className="flex items-baseline gap-3 flex-wrap">
                <span className="text-3xl font-bold text-(--sea-ink)">
                  {product.price.toLocaleString()} ₽
                </span>
                {product.old_price && (
                  <span className="text-lg text-(--sea-ink-soft) line-through">
                    {product.old_price.toLocaleString()} ₽
                  </span>
                )}
                {product.discount && (
                  <span className="rounded bg-red-500 px-2 py-1 text-sm font-semibold text-white">
                    -{product.discount}%
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90">
                <ShoppingCart className="size-4" />
                В корзину
              </button>
              <button 
                className="rounded-lg border border-(--line) p-3 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
                aria-label="Добавить в избранное"
              >
                <Heart className="size-5" />
              </button>
              <button 
                className="rounded-lg border border-(--line) p-3 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
                aria-label="Поделиться"
              >
                <Share2 className="size-5" />
              </button>
            </div>

            {/* Seller Info */}
            {product.seller_name && (
              <div className="rounded-lg border border-(--line) p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-(--sea-ink-soft)">Продавец</p>
                    <p className="font-medium text-(--sea-ink)">{product.seller_name}</p>
                  </div>
                  {product.seller_rating && (
                    <div className="text-sm text-(--sea-ink-soft)">
                      ★ {product.seller_rating}/5
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Description */}
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-(--sea-ink)">
                Описание
              </h2>
              <p className="text-(--sea-ink-soft) leading-relaxed whitespace-pre-wrap">
                {product.description || 'Описание товара будет добавлено позже.'}
              </p>
            </div>

            {/* Specifications */}
            {product.specifications && Object.keys(product.specifications).length > 0 && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-(--sea-ink)">
                  Характеристики
                </h2>
                <div className="rounded-lg border border-(--line) divide-y divide-(--line)">
                  {Object.entries(product.specifications).map(([key, value]) => (
                    <div key={key} className="flex py-3">
                      <span className="w-1/3 text-(--sea-ink-soft)">{key}</span>
                      <span className="w-2/3 font-medium text-(--sea-ink)">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Meta Info */}
            <div className="rounded-lg bg-(--link-bg-hover) p-4 text-sm text-(--sea-ink-soft)">
              <div className="flex justify-between">
                <span>Артикул:</span>
                <span className="font-medium text-(--sea-ink)">#{product.id}</span>
              </div>
              <div className="flex justify-between mt-2">
                <span>Добавлено:</span>
                <span className="font-medium text-(--sea-ink)">
                  {new Date(product.created_at).toLocaleDateString('ru-RU')}
                </span>
              </div>
              {product.category && (
                <div className="flex justify-between mt-2">
                  <span>Категория:</span>
                  <span className="font-medium text-(--sea-ink)">{product.category}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}