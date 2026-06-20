// src/components/features/product-detail.tsx
import { useParams } from '@tanstack/react-router'
import { ArrowLeft, Heart, Share2, MessageCircle, Star, User, CheckCircle, Shield } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { productQueryOptions } from '@/lib/queries/ads'
import { useState } from 'react'
import { Review, Seller } from '@/types/products'


// Компонент карусели изображений
function ImageCarousel({ images, alt }: { images: string[]; alt: string }) {
  const [currentIndex, setCurrentIndex] = useState(0)

  if (!images.length) return null

  const next = () => setCurrentIndex((i) => (i + 1) % images.length)
  const prev = () => setCurrentIndex((i) => (i - 1 + images.length) % images.length)

  return (
    <div className="space-y-4">
      {/* Main image */}
      <div className="relative aspect-square overflow-hidden rounded-lg bg-gray-50">
        <img
          src={images[currentIndex]}
          alt={`${alt} ${currentIndex + 1}`}
          className="h-full w-full object-cover"
        />
        
        {/* Navigation buttons */}
        {images.length > 1 && (
          <>
            <button
              onClick={prev}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-(--sea-ink) shadow hover:bg-white"
              aria-label="Предыдущее фото"
            >
              <ArrowLeft className="size-5" />
            </button>
            <button
              onClick={next}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-white/80 p-2 text-(--sea-ink) shadow hover:bg-white"
              aria-label="Следующее фото"
            >
              <ArrowLeft className="size-5 rotate-180" />
            </button>
          </>
        )}
        
        {/* Counter */}
        {images.length > 1 && (
          <div className="absolute bottom-2 right-2 rounded bg-black/50 px-2 py-1 text-xs text-white">
            {currentIndex + 1} / {images.length}
          </div>
        )}
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {images.map((img, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`shrink-0 aspect-square w-16 overflow-hidden rounded border-2 transition ${
                currentIndex === idx
                  ? 'border-(--palm)'
                  : 'border-(--line) hover:border-(--palm)/50'
              }`}
            >
              <img
                src={img}
                alt={`${alt} thumb ${idx + 1}`}
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Компонент рейтинга
function StarRating({ rating, count }: { rating: number; count?: number }) {
  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`size-4 ${
              star <= Math.round(rating)
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300'
            }`}
          />
        ))}
      </div>
      <span className="text-sm font-medium text-(--sea-ink)">{rating.toFixed(1)}</span>
      {count !== undefined && (
        <span className="text-sm text-(--sea-ink-soft)">({count})</span>
      )}
    </div>
  )
}

// Компонент карточки отзыва
function ReviewCard({ review }: { review: Review }) {
  return (
    <div className="rounded-lg border border-(--line) p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-(--sea-ink)">
            {review.reviewer_username || `Пользователь #${review.reviewer_tg_id}`}
          </p>
          <StarRating rating={review.rating} />
        </div>
        <span className="text-xs text-(--sea-ink-soft)">
          {new Date(review.created_at).toLocaleDateString('ru-RU')}
        </span>
      </div>
      {review.comment && (
        <p className="mt-2 text-sm text-(--sea-ink-soft)">{review.comment}</p>
      )}
    </div>
  )
}

// Компонент информации о продавце
function SellerInfo({ seller }: { seller: Seller }) {
  return (
    <div className="rounded-lg border border-(--line) p-4">
      <div className="flex items-center gap-3">
        <div className="flex size-12 items-center justify-center rounded-full bg-(--link-bg-hover)">
          <User className="size-6 text-(--sea-ink-soft)" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-(--sea-ink)">
            {seller.username || `${seller.first_name || ''} ${seller.last_name || ''}`.trim() || 'Продавец'}
          </p>
          <StarRating rating={seller.rating} count={seller.review_count} />
        </div>
      </div>

      {/* Badges */}
      <div className="mt-3 flex flex-wrap gap-2">
        {seller.is_trusted_seller && (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 text-xs font-medium text-green-700">
            <CheckCircle className="size-3" />
            Проверенный продавец
          </span>
        )}
        {seller.is_moderator && (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700">
            <Shield className="size-3" />
            Модератор
          </span>
        )}
      </div>

      {/* Reviews */}
      {seller.reviews.length > 0 && (
        <div className="mt-4 space-y-3">
          <h4 className="text-sm font-semibold text-(--sea-ink)">Отзывы</h4>
          {seller.reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
        </div>
      )}
    </div>
  )
}

export function ProductDetail() {
  const { productId } = useParams({ from: '/_app/product/$productId' })

  const { data: product, isLoading, isError, error } = useQuery(
    productQueryOptions(productId)
  )

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
          <div>
            <ImageCarousel 
              images={product.image_urls} 
              alt={product.title} 
            />
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
              {product.seller?.username ? (
                <a
                  href={`https://t.me/${product.seller.username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90"
                >
                  <MessageCircle className="size-4" />
                  Связаться с продавцом
                </a>
              ) : (
                <button className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90">
                  <MessageCircle className="size-4" />
                  Связаться с продавцом
                </button>
              )}
              <button 
                className="rounded-lg border border-(--line) p-3 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
                aria-label="Добавить в избранное"
              >
                <Heart className="size-5" />
              </button>
            </div>

            {/* Seller Info */}
            {product.seller && <SellerInfo seller={product.seller} />}

            {/* Description */}
            {product.description && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-(--sea-ink)">
                  Описание
                </h2>
                <p className="text-(--sea-ink-soft) leading-relaxed whitespace-pre-wrap">
                  {product.description}
                </p>
              </div>
            )}

            {/* Specifications */}
            <div className="rounded-lg bg-(--link-bg-hover) p-4 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div className="flex justify-between">
                  <span className="text-(--sea-ink-soft)">Артикул:</span>
                  <span className="font-medium text-(--sea-ink)">#{product.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-(--sea-ink-soft)">Категория:</span>
                  <span className="font-medium text-(--sea-ink)">{product.category}</span>
                </div>
                {product.subcategory && (
                  <div className="flex justify-between">
                    <span className="text-(--sea-ink-soft)">Подкатегория:</span>
                    <span className="font-medium text-(--sea-ink)">{product.subcategory}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-(--sea-ink-soft)">Город:</span>
                  <span className="font-medium text-(--sea-ink)">{product.city}</span>
                </div>
                {product.size && (
                  <div className="flex justify-between">
                    <span className="text-(--sea-ink-soft)">Размер:</span>
                    <span className="font-medium text-(--sea-ink)">{product.size}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-(--sea-ink-soft)">Состояние:</span>
                  <span className="font-medium text-(--sea-ink)">
                    {product.condition === 'new' ? 'Новое' : 
                     product.condition === 'used' ? 'Б/У' : 
                     product.condition === 'unknown' ? 'Не указано' : product.condition}
                  </span>
                </div>
                <div className="flex justify-between col-span-2">
                  <span className="text-(--sea-ink-soft)">Добавлено:</span>
                  <span className="font-medium text-(--sea-ink)">
                    {new Date(product.created_at).toLocaleDateString('ru-RU')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}