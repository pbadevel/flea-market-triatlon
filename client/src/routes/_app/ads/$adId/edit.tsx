// src/routes/_app/ads/$adId/edit.tsx
import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Upload,
  X,
  Save,
  AlertCircle,
} from 'lucide-react'
import { fetchAdForEdit, updateAd } from '@/lib/api/client/ads'
import { filtersQueryOptions } from '@/lib/queries/ads'
import { verifySession } from '@/lib/session'

export const Route = createFileRoute('/_app/ads/$adId/edit')({
  loader: async () => {
    const sessionData = await verifySession()
    return sessionData
  },
  component: EditAdPage,
})

interface PhotoItem {
  /** ID существующего фото с сервера (undefined для загруженных) */
  id?: number;
  /** File объект для новых фото (undefined для существующих) */
  file?: File;
  /** URL превью (серверный URL или blob) */
  url: string;
}

function EditAdPage() {
  const { token } = Route.useLoaderData()
  const { adId } = Route.useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [formData, setFormData] = useState({
    title: '',
    price: '',
    category: '',
    subcategory: '',
    country: '',
    city: '',
    size: '',
    condition: '',
    description: '',
    ad_type: 'Продажа',
    contact_method: 'telegram',
  })
  
  const [photoItems, setPhotoItems] = useState<PhotoItem[]>([])
  const [error, setError] = useState('')

  const { data: ad, isLoading: adLoading } = useQuery({
    queryKey: ['ad', adId],
    queryFn: () => fetchAdForEdit(token!, parseInt(adId)),
    enabled: !!token && !!adId,
  })

  const { data: filterConfig } = useQuery(filtersQueryOptions())

  useEffect(() => {
    if (ad) {
      setFormData({
        title: ad.title,
        price: ad.price.toString(),
        category: ad.category,
        subcategory: ad.subcategory || '',
        country: ad.country || '',
        city: ad.city,
        size: ad.size || '',
        condition: ad.condition,
        description: ad.description || '',
        ad_type: ad.ad_type,
        contact_method: ad.contact_method,
      })
      
      if (ad.image_urls && ad.image_urls.length > 0) {
        const items: PhotoItem[] = (ad.image_urls || []).map((url, i) => ({
          id: ad.photo_ids?.[i],
          url,
        }))
        setPhotoItems(items)
      }
    }
  }, [ad])

  const updateMutation = useMutation({
    mutationFn: async () => {
      const data = new FormData()
      data.append('title', formData.title)
      data.append('price', formData.price)
      data.append('city', formData.city)
      if (formData.country) data.append('country', formData.country)
      data.append('category', formData.category)
      if (formData.subcategory) data.append('subcategory', formData.subcategory)
      if (formData.size) data.append('size', formData.size)
      data.append('condition', formData.condition)
      if (formData.description) data.append('description', formData.description)
      data.append('ad_type', formData.ad_type)
      data.append('contact_method', formData.contact_method)

      // Какие существующие фото оставить
      const keepIds = photoItems
        .filter(p => p.id !== undefined)
        .map(p => p.id!)
      keepIds.forEach(id => data.append('keep_photo_ids', id.toString()))

      // Новые фото
      photoItems
        .filter(p => p.file !== undefined)
        .forEach(p => data.append('photos', p.file!))

      return await updateAd(token!, parseInt(adId), data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-ads'] })
      navigate({ to: '/' })
    },
    onError: (err) => {
      setError(err.message || 'Ошибка при обновлении объявления')
    },
  })

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const maxNew = 10 - photoItems.length
    const newItems: PhotoItem[] = files.slice(0, maxNew).map(file => ({
      file,
      url: URL.createObjectURL(file),
    }))
    setPhotoItems(prev => [...prev, ...newItems])
  }

  const removePhoto = (index: number) => {
    setPhotoItems(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.title || !formData.price || !formData.city || !formData.category) {
      setError('Заполните все обязательные поля')
      return
    }

    updateMutation.mutate()
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Требуется авторизация
          </h1>
          <Link to="/auth/login" className="text-(--palm) hover:underline">
            Войти
          </Link>
        </div>
      </div>
    )
  }

  if (adLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-(--sea-ink-soft)">Загрузка...</div>
      </div>
    )
  }

  if (!ad) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-(--sea-ink) mb-4">
            Объявление не найдено
          </h1>
          <Link to="/my-ads" className="text-(--palm) hover:underline">
            К моим объявлениям
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
              to="/my-ads"
              className="flex items-center gap-1 text-(--sea-ink-soft) hover:text-(--sea-ink)"
            >
              <ArrowLeft className="size-5" />
              <span className="text-sm">Назад</span>
            </Link>
            <h1 className="text-lg font-semibold text-(--sea-ink)">
              Редактировать объявление
            </h1>
          </div>
        </div>
      </header>

      <div className="page-wrap py-8">
        {ad.status === 'rejected' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="size-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-800 mb-1">
                  Объявление было отклонено
                </h3>
                <p className="text-sm text-red-700">
                  Причина: {ad.rejection_reason || 'Не указана'}
                </p>
                <p className="text-sm text-red-600 mt-2">
                  Внесите изменения и отправьте на повторную модерацию
                </p>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl space-y-6">
          {/* Photos */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Фотографии
            </label>
            <div className="grid grid-cols-3 gap-3">
              {photoItems.map((item, index) => (
                <div key={index} className="relative aspect-square">
                  <img
                    src={item.url}
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
              {photoItems.length < 10 && (
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
                      {photoItems.length}/10
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
            <input
              type="text"
              required
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              className="w-full rounded-lg border border-(--line) px-4 py-2 text-(--sea-ink) focus:border-(--palm) focus:outline-none"
              placeholder="Москва"
            />
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

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
            >
              <Save className="size-4" />
              {updateMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
            <Link
              to="/my-ads"
              className="flex items-center justify-center rounded-lg border border-(--line) px-6 py-3 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
            >
              Отмена
            </Link>
          </div>

          <p className="text-center text-xs text-(--sea-ink-soft)">
            После сохранения объявление будет отправлено на повторную модерацию
          </p>
        </form>
      </div>
    </div>
  )
}