// src/components/features/product-detail.tsx
import { useParams } from '@tanstack/react-router'
import { ArrowLeft, Heart, Share2, MessageCircle, Star, User, CheckCircle, Shield, Send, Mail, Phone } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productQueryOptions } from '@/lib/queries/ads'
import { createReview } from '@/lib/api/client/reviews'
import { useState } from 'react'
import { Review, Seller, ReviewCreate } from '@/types/products'

// Компонент карусели изображений
function ImageCarousel({ images, alt }: { images: string[]; alt: string }) {
  const [currentIndex, setCurrentIndex] = useState(0)

  if (!images.length) return null

  const next = () => setCurrentIndex((i) => (i + 1) % images.length)
  const prev = () => setCurrentIndex((i) => (i - 1 + images.length) % images.length)

  return (
    <div className="space-y-4 w-full">
      {/* Главный контейнер: w-full + overflow-hidden гарантируют, что ничего не вылезет */}
      <div className="relative w-full overflow-hidden rounded-lg bg-gray-50 aspect-[4/5] sm:aspect-square max-h-[65vh]">
        <img
          src={images[currentIndex]}
          alt={`${alt} ${currentIndex + 1}`}
          className="block w-full h-full object-cover" /* block критически важен! */
        />
        
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
        
        {images.length > 1 && (
          <div className="absolute bottom-2 right-2 rounded bg-black/50 px-2 py-1 text-xs text-white backdrop-blur-sm">
            {currentIndex + 1} / {images.length}
          </div>
        )}
      </div>

      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto scrollbar-none pb-2 w-full">
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
                className="block h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// Компонент рейтинга
// Кликабельные звёзды для формы отзыва
function ClickableStars({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          className="transition hover:scale-110"
        >
          <Star
            className={`size-8 ${
              star <= value
                ? 'fill-yellow-400 text-yellow-400'
                : 'text-gray-300 hover:text-yellow-300'
            }`}
          />
        </button>
      ))}
    </div>
  )
}

// Форма отзыва
function ReviewForm({ adId, sellerId, token }: { adId: number; sellerId: number; token: string | null }) {
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [showForm, setShowForm] = useState(false)
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (data: ReviewCreate) => createReview(token!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', adId] })
      setRating(0)
      setComment('')
      setShowForm(false)
    },
  })

  if (!showForm) {
    return (
      <button
        onClick={() => {
          if (!token) {
            window.location.href = '/auth/login'
            return
          }
          setShowForm(true)
        }}
        className="w-full py-2 text-sm text-(--sea-ink-soft) hover:text-(--palm) transition text-left"
      >
        {token ? 'Оставить отзыв' : 'Оставить отзыв →'}
      </button>
    )
  }

  if (!token) {
    return null
  }

  return (
    <div className="rounded-lg border border-(--line) p-4 space-y-3">
      <h4 className="text-sm font-semibold text-(--sea-ink)">Ваша оценка</h4>
      <ClickableStars value={rating} onChange={setRating} />
      
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Комментарий (необязательно)"
        rows={3}
        maxLength={500}
        className="w-full rounded-lg border border-(--line) px-3 py-2 text-sm text-(--sea-ink) focus:border-(--palm) focus:outline-none resize-none"
      />
      
      <div className="flex gap-2">
        <button
          onClick={() => mutation.mutate({ ad_id: adId, rating, comment: comment || undefined })}
          disabled={rating === 0 || mutation.isPending}
          className="flex items-center gap-1 rounded-lg bg-(--palm) px-4 py-2 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50 transition"
        >
          <Send className="size-3.5" />
          {mutation.isPending ? 'Отправка...' : 'Отправить'}
        </button>
        <button
          onClick={() => setShowForm(false)}
          className="rounded-lg border border-(--line) px-4 py-2 text-sm text-(--sea-ink-soft) hover:bg-(--link-bg-hover)"
        >
          Отмена
        </button>
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-500">{mutation.error.message}</p>
      )}
    </div>
  )
}

// Умная кнопка связи — показывает доступные способы
function ContactSellerButton({ seller }: { seller: Seller | null }) {
  const [showOptions, setShowOptions] = useState(false)

  if (!seller) return null

  const preferred = seller.preferred_contact
  const contactVal = seller.contact_value || ''

  // Построить contact по предпочтению
  const getPreferredContact = (): { icon: React.ReactNode; label: string; href: string } | null => {
    if (preferred === 'TELEGRAM') {
      const tg = seller.username || contactVal
      if (tg) return { icon: <MessageCircle className="size-4" />, label: 'Написать в Telegram', href: `https://t.me/${tg.replace('@', '')}` }
    }
    if (preferred === 'EMAIL') {
      const email = seller.email || contactVal
      if (email) return { icon: <Mail className="size-4" />, label: 'Написать на Email', href: `mailto:${email}` }
    }
    if (preferred === 'PHONE') {
      const phone = seller.phone || contactVal
      if (phone) return { icon: <Phone className="size-4" />, label: 'Позвонить', href: `tel:${phone}` }
    }
    if (preferred === 'MAX') {
      if (contactVal) return { icon: <Send className="size-4" />, label: 'Написать в MAX', href: `https://max.ru/user/${contactVal}` }
    }
    return null
  }

  const preferredContact = getPreferredContact()

  // Все доступные контакты
  const contacts: { icon: React.ReactNode; label: string; href: string }[] = []

  if (seller.username) {
    contacts.push({
      icon: <MessageCircle className="size-4" />,
      label: 'Telegram',
      href: `https://t.me/${seller.username}`,
    })
  }
  if (seller.email) {
    contacts.push({
      icon: <Mail className="size-4" />,
      label: 'Email',
      href: `mailto:${seller.email}`,
    })
  }
  if (seller.phone) {
    contacts.push({
      icon: <Phone className="size-4" />,
      label: 'Позвонить',
      href: `tel:${seller.phone}`,
    })
  }
  if (preferred === 'MAX' && contactVal && !contacts.find(c => c.label === 'MAX')) {
    contacts.push({
      icon: <Send className="size-4" />,
      label: 'MAX',
      href: `https://max.ru/user/${contactVal}`,
    })
  }

  if (contacts.length === 0) {
    return (
      <button
        disabled
        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm)/50 py-3 text-sm font-medium text-white cursor-not-allowed"
      >
        <MessageCircle className="size-4" />
        Нет контактов
      </button>
    )
  }

  // Если есть предпочтительный — показываем его крупной кнопкой
  if (preferredContact) {
    return (
      <div className="flex flex-col gap-2">
        <a
          href={preferredContact.href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 transition"
        >
          {preferredContact.icon}
          {preferredContact.label}
        </a>
        {contacts.length > 1 && (
          <button
            onClick={() => setShowOptions(!showOptions)}
            className="text-xs text-(--sea-ink-soft) hover:underline"
          >
            {showOptions ? 'Скрыть другие способы' : 'Другие способы связи'}
          </button>
        )}
        {showOptions && (
          <div className="flex flex-col gap-2">
            {contacts.filter(c => c.label !== preferredContact.label).map((c, i) => (
              <a
                key={i}
                href={c.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-lg border border-(--line) px-4 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
              >
                {c.icon}
                {c.label}
              </a>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Fallback — показываем все доступные
  if (contacts.length === 1) {
    const c = contacts[0]
    return (
      <a
        href={c.href}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 transition"
      >
        {c.icon}
        {c.label}
      </a>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => setShowOptions(!showOptions)}
        className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 transition"
      >
        <Send className="size-4" />
        Связаться с продавцом
      </button>
      {showOptions && (
        <div className="flex flex-col gap-2">
          {contacts.map((c, i) => (
            <a
              key={i}
              href={c.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-lg border border-(--line) px-4 py-2 text-sm text-(--sea-ink) hover:bg-(--link-bg-hover) transition"
            >
              {c.icon}
              {c.label}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

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
            {review.reviewer_username || `Пользователь #${review.reviewer_user_id}`}
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
function SellerInfo({ seller, adId, token }: { seller: Seller; adId: number; token: string | null }) {
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

      {/* Отзывы */}
      <div className="mt-4 space-y-3">
        <h4 className="text-sm font-semibold text-(--sea-ink)">
          Отзывы
          {seller.review_count > 0 && (
            <span className="text-xs font-normal text-(--sea-ink-soft) ml-1">({seller.review_count})</span>
          )}
        </h4>
        {seller.reviews.length > 0 ? (
          seller.reviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))
        ) : (
          <p className="text-sm text-(--sea-ink-soft)">Пока нет отзывов. Будьте первыми!</p>
        )}
      </div>

      {/* Форма отзыва */}
      <div className="mt-4">
        <ReviewForm adId={adId} sellerId={seller.id} token={token} />
      </div>
    </div>
  )
}

export function ProductDetail({ token }: { token?: string | null }) {
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

            {/* Actions — умная кнопка связи */}
            <div className="flex gap-3">
              <ContactSellerButton seller={product.seller} />
              {/* <button 
                className="rounded-lg border border-(--line) p-3 text-(--sea-ink-soft) hover:bg-(--link-bg-hover) hover:text-(--sea-ink)"
                aria-label="Добавить в избранное"
              >
                <Heart className="size-5" />
              </button> */}
            </div>

            {/* Seller Info */}
            {product.seller && <SellerInfo seller={product.seller} adId={product.id} token={token ?? null} />}

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
              <div className="space-y-2">
                <div className="flex justify-between gap-2">
                  <span className="text-(--sea-ink-soft) shrink-0">Артикул:</span>
                  <span className="font-medium text-(--sea-ink) text-right break-words">#{product.id}</span>
                </div>
                <div className="flex justify-between gap-2">
                  <span className="text-(--sea-ink-soft) shrink-0">Категория:</span>
                  <span className="font-medium text-(--sea-ink) text-right break-words">{product.category}</span>
                </div>
                {product.subcategory && (
                  <div className="flex justify-between gap-2">
                    <span className="text-(--sea-ink-soft) shrink-0">Подкатегория:</span>
                    <span className="font-medium text-(--sea-ink) text-right break-words">{product.subcategory}</span>
                  </div>
                )}
                <div className="flex justify-between gap-2">
                  <span className="text-(--sea-ink-soft) shrink-0">Город:</span>
                  <span className="font-medium text-(--sea-ink) text-right break-words">{product.city}</span>
                </div>
                {product.size && (
                  <div className="flex justify-between gap-2">
                    <span className="text-(--sea-ink-soft) shrink-0">Размер:</span>
                    <span className="font-medium text-(--sea-ink) text-right break-words">{product.size}</span>
                  </div>
                )}
                <div className="flex justify-between gap-2">
                  <span className="text-(--sea-ink-soft) shrink-0">Состояние:</span>
                  <span className="font-medium text-(--sea-ink) text-right break-words">
                    {product.condition === 'new' ? 'Новое' : 
                    product.condition === 'used' ? 'Б/У' : 
                    product.condition === 'unknown' ? 'Не указано' : product.condition}
                  </span>
                </div>
                <div className="flex justify-between gap-2">
                  <span className="text-(--sea-ink-soft) shrink-0">Добавлено:</span>
                  <span className="font-medium text-(--sea-ink) text-right break-words">
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