// src/routes/create-ad.tsx
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Upload, X } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { createAd } from '@/lib/api/client/ads'
import { filtersQueryOptions } from '@/lib/queries/ads'
import { verifySession } from '@/lib/session'

export const Route = createFileRoute('/_app/create-ad')({
  loader: async () => {
    // Резолвим сессию в loader
    const token = await verifySession()
    
    return {
      isAuthenticated: !!token,
      token: token ?? null,
    }
  },
  component: CreateAdPage,
})

function CreateAdPage() {
  const navigate = useNavigate()
  const { token } = Route.useLoaderData()

  const [formData, setFormData] = useState({
    title: '',
    price: '',
    city: 'Москва',
    country: 'Россия',
    category: '',
    subcategory: '',
    size: '',
    condition: 'used',
    description: '',
    ad_type: 'Продажа',
    contact_method: 'telegram',
  })

  const [photos, setPhotos] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])

  const { data: filterConfig } = useQuery(filtersQueryOptions())

  const createMutation = useMutation({
    mutationFn: (data: FormData) => createAd(data, token!),
    onSuccess: () => {
      navigate({ to: '/my-ads' })
    },
    onError: (error) => {
      alert(`Ошибка: ${error.message}`)
    },
  })

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newPhotos = [...photos, ...files].slice(0, 10)
    setPhotos(newPhotos)

    const newPreviews = newPhotos.map((file) => URL.createObjectURL(file))
    setPreviews(newPreviews)
  }

  const removePhoto = (index: number) => {
    const newPhotos = photos.filter((_, i) => i !== index)
    const newPreviews = previews.filter((_, i) => i !== index)
    setPhotos(newPhotos)
    setPreviews(newPreviews)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!token) {
      alert('Необходима авторизация')
      return
    }

    if (photos.length === 0) {
      alert('Добавьте хотя бы одно фото')
      return
    }

    const data = new FormData()
    data.append('title', formData.title)
    data.append('price', formData.price)
    data.append('city', formData.city)
    data.append('country', formData.country)
    data.append('category', formData.category)
    if (formData.subcategory) data.append('subcategory', formData.subcategory)
    if (formData.size) data.append('size', formData.size)
    data.append('condition', formData.condition)
    if (formData.description) data.append('description', formData.description)
    data.append('ad_type', formData.ad_type)
    data.append('contact_method', formData.contact_method)

    photos.forEach((photo) => {
      data.append('photos', photo)
    })

    createMutation.mutate(data)
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Требуется авторизация
          </h1>
          <p className="text-(--sea-ink-soft) mb-6">
            Войдите через Telegram для создания объявления
          </p>
          <Link to="/" className="text-(--palm) hover:underline">
            На главную
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
            <h1 className="text-lg font-semibold text-(--sea-ink)">
              Новое объявление
            </h1>
          </div>
        </div>
      </header>

      {/* Form */}
      <div className="page-wrap py-8">
        <form onSubmit={handleSubmit} className="mx-auto mb-20 max-w-2xl space-y-6">
          {/* Photos */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Фотографии *
            </label>
            <div className="grid grid-cols-3 gap-3">
              {previews.map((preview, index) => (
                <div key={index} className="relative aspect-square">
                  <img
                    src={preview}
                    alt={`Preview ${index + 1}`}
                    className="h-full w-full rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removePhoto(index)}
                    className="absolute right-1 top-1 rounded-full bg-red-500 p-1 text-white hover:bg-red-600"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              ))}
              {photos.length < 10 && (
                <label className="flex aspect-square cursor-pointer items-center justify-center rounded-lg border-2 border-dashed border-(--line) hover:border-(--palm)">
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={handlePhotoChange}
                    className="hidden"
                  />
                  <div className="text-center">
                    <Upload className="mx-auto size-8 text-(--sea-ink-soft)" />
                    <p className="mt-2 text-xs text-(--sea-ink-soft)">
                      {photos.length}/10
                    </p>
                  </div>
                </label>
              )}
            </div>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Название *
            </label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              placeholder="Например: Гидрокостюм Zone3"
            />
          </div>

          {/* Price */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Цена (₽) *
            </label>
            <input
              type="number"
              required
              min="0"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              placeholder="0"
            />
          </div>

          {/* Category */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Категория *
            </label>
            <select
              required
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            >
              <option value="">Выберите категорию</option>
              {filterConfig?.categories.map((cat) => (
                <option key={cat.key} value={cat.key}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* City */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Город *
            </label>
            <select
              required
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            >
              <option value="Москва">Москва</option>
              <option value="Санкт-Петербург">Санкт-Петербург</option>
              <option value="Сочи">Сочи</option>
              <option value="Краснодар">Краснодар</option>
              <option value="Казань">Казань</option>
              <option value="Екатеринбург">Екатеринбург</option>
              <option value="Новосибирск">Новосибирск</option>
            </select>
          </div>

          {/* Condition */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Состояние *
            </label>
            <select
              required
              value={formData.condition}
              onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            >
              <option value="new">Новое</option>
              <option value="used">Б/У</option>
              <option value="unknown">Не указано</option>
            </select>
          </div>

          {/* Size */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Размер
            </label>
            <input
              type="text"
              value={formData.size}
              onChange={(e) => setFormData({ ...formData, size: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              placeholder="M, L, 48, 50..."
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Описание
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={5}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              placeholder="Расскажите подробнее о товаре..."
            />
          </div>

          {/* Submit */}
          <p className="text-center text-xs text-(--sea-ink-soft)">
            После отправки объявление пройдет модерацию и будет опубликовано
          </p>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="w-full rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
          >
            {createMutation.isPending ? 'Отправка...' : 'Отправить на модерацию'}
          </button>

        </form>
      </div>
    </div>
  )
}