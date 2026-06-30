// src/routes/_app/ads/$adId/edit.tsx
import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Upload,
  X,
  Save,
  AlertCircle,
  ChevronDown,
} from 'lucide-react'
import { fetchAdForEdit, updateAd, submitForModeration } from '@/lib/api/client/ads'
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
  id?: number;
  file?: File;
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
  const [saved, setSaved] = useState(false)

  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false)
  const [showSubcategoryDropdown, setShowSubcategoryDropdown] = useState(false)
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [showCityDropdown, setShowCityDropdown] = useState(false)
  const [customCity, setCustomCity] = useState('')
  const [useCustomCity, setUseCustomCity] = useState(false)

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
        const items: PhotoItem[] = ad.image_urls.map((url, i) => ({
          id: ad.photo_ids?.[i],
          url,
        }))
        setPhotoItems(items)
      }
    }
  }, [ad])

  const availableSubcategories = useMemo(() => {
    if (!filterConfig || !formData.category) return []

    const category = filterConfig.categories.find(c => c.key === formData.category)
    if (!category) return []

    const items: { group?: string; item: { key: string; label: string; requires_size?: boolean } }[] = []

    if (category.groups) {
      category.groups.forEach(group => {
        group.items.forEach(item => {
          items.push({ group: group.name, item })
        })
      })
    }

    if (category.items) {
      category.items.forEach(item => {
        items.push({ item })
      })
    }

    return items
  }, [filterConfig, formData.category])

  const needsSize = useMemo(() => {
    if (!formData.subcategory || !availableSubcategories.length) return false
    const found = availableSubcategories.find(s => s.item.key === formData.subcategory)
    return found?.item.requires_size ?? false
  }, [formData.subcategory, availableSubcategories])

  const availableCities = useMemo(() => {
    if (!filterConfig) return []

    const cities = new Set<string>()

    filterConfig.default_cities.forEach(city => cities.add(city))

    if (formData.country) {
      const country = filterConfig.countries.find(c => c.key === formData.country)
      if (country) {
        country.cities.forEach(city => cities.add(city))
      }
    }

    return Array.from(cities).sort((a, b) => a.localeCompare(b, 'ru'))
  }, [filterConfig, formData.country])

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

      const keepIds = photoItems
        .filter(p => p.id !== undefined)
        .map(p => p.id!)
      keepIds.forEach(id => data.append('keep_photo_ids', id.toString()))

      photoItems
        .filter(p => p.file !== undefined)
        .forEach(p => data.append('photos', p.file!))

      return await updateAd({ token: token!, adId: parseInt(adId), formData: data })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-ads'] })
      queryClient.invalidateQueries({ queryKey: ['ad-edit', adId] })
      setSaved(true)
    },
    onError: (err) => {
      setError(err.message || 'Ошибка при обновлении объявления')
    },
  })

  const submitMut = useMutation({
    mutationFn: () => submitForModeration(token!, parseInt(adId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-ads'] })
      navigate({ to: '/my-ads' })
    },
    onError: (err) => {
      setError(err.message || 'Ошибка при отправке на модерацию')
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

    if (!formData.title || !formData.price || !formData.city || !formData.category || !formData.condition) {
      setError('Заполните все обязательные поля')
      return
    }

    const totalSize = photoItems
      .filter(p => p.file)
      .reduce((sum, p) => sum + (p.file?.size || 0), 0)
    if (totalSize > 50 * 1024 * 1024) {
      setError(`Общий размер новых фотографий ${(totalSize / 1024 / 1024).toFixed(1)} МБ превышает лимит 50 МБ.`)
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

  const currentCategory = filterConfig?.categories.find(c => c.key === formData.category)
  const currentCountry = filterConfig?.countries.find(c => c.key === formData.country)

  return (
    <div className="min-h-screen bg-(--bg)">
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
              className="w-full rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
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
              className="w-full rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
              placeholder="0"
            />
          </div>

          {/* Category */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Категория *
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowCategoryDropdown(!showCategoryDropdown)
                  setShowSubcategoryDropdown(false)
                  setShowCountryDropdown(false)
                  setShowCityDropdown(false)
                }}
                className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
              >
                <span className={formData.category ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                  {currentCategory?.label || 'Выберите категорию'}
                </span>
                <ChevronDown className="size-4 text-(--sea-ink-soft)" />
              </button>

              {showCategoryDropdown && filterConfig && (
                <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                  {filterConfig.categories.map((cat) => (
                    <button
                      key={cat.key}
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, category: cat.key, subcategory: '' })
                        setShowCategoryDropdown(false)
                      }}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                        formData.category === cat.key
                          ? 'bg-(--palm)/10 text-(--palm) font-medium'
                          : 'text-(--sea-ink)'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Subcategory */}
          {formData.category && availableSubcategories.length > 0 && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-(--sea-ink)">
                Подкатегория
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setShowSubcategoryDropdown(!showSubcategoryDropdown)
                    setShowCategoryDropdown(false)
                    setShowCountryDropdown(false)
                    setShowCityDropdown(false)
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
                >
                  <span className={formData.subcategory ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                    {formData.subcategory
                      ? availableSubcategories.find(s => s.item.key === formData.subcategory)?.item.label || 'Выберите подкатегорию'
                      : 'Выберите подкатегорию (необязательно)'}
                  </span>
                  <ChevronDown className="size-4 text-(--sea-ink-soft)" />
                </button>

                {showSubcategoryDropdown && (
                  <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                    {availableSubcategories.map(({ group, item }, idx) => (
                      <div key={idx}>
                        {group && (idx === 0 || availableSubcategories[idx - 1].group !== group) && (
                          <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50 sticky top-0">
                            {group}
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            setFormData({ ...formData, subcategory: item.key })
                            setShowSubcategoryDropdown(false)
                          }}
                          className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                            formData.subcategory === item.key
                              ? 'bg-(--palm)/10 text-(--palm) font-medium'
                              : 'text-(--sea-ink)'
                          }`}
                        >
                          {item.label}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Country */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Страна
            </label>
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowCountryDropdown(!showCountryDropdown)
                  setShowCategoryDropdown(false)
                  setShowSubcategoryDropdown(false)
                  setShowCityDropdown(false)
                }}
                className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
              >
                <span className={formData.country ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                  {currentCountry ? `${currentCountry.flag} ${currentCountry.name}` : 'Выберите страну (необязательно)'}
                </span>
                <ChevronDown className="size-4 text-(--sea-ink-soft)" />
              </button>

              {showCountryDropdown && filterConfig && (
                <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setFormData({ ...formData, country: '', city: '' })
                      setShowCountryDropdown(false)
                    }}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                      !formData.country
                        ? 'bg-(--palm)/10 text-(--palm) font-medium'
                        : 'text-(--sea-ink)'
                    }`}
                  >
                    Не указана
                  </button>
                  {filterConfig.countries.map((country) => (
                    <button
                      key={country.key}
                      type="button"
                      onClick={() => {
                        setFormData({ ...formData, country: country.key, city: '' })
                        setShowCountryDropdown(false)
                      }}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                        formData.country === country.key
                          ? 'bg-(--palm)/10 text-(--palm) font-medium'
                          : 'text-(--sea-ink)'
                      }`}
                    >
                      {country.flag} {country.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* City */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Город *
            </label>

            {useCustomCity ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customCity}
                  onChange={(e) => setCustomCity(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && customCity.trim()) {
                      setFormData({ ...formData, city: customCity.trim() })
                      setUseCustomCity(false)
                      setCustomCity('')
                    }
                  }}
                  placeholder="Введите город"
                  className="flex-1 rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => {
                    if (customCity.trim()) {
                      setFormData({ ...formData, city: customCity.trim() })
                      setUseCustomCity(false)
                      setCustomCity('')
                    }
                  }}
                  className="rounded-lg bg-(--palm) px-4 py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90"
                >
                  OK
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUseCustomCity(false)
                    setCustomCity('')
                  }}
                  className="rounded-lg border border-(--line) px-3 py-2.5 text-(--sea-ink-soft) hover:bg-(--link-bg-hover)"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setShowCityDropdown(!showCityDropdown)
                    setShowCategoryDropdown(false)
                    setShowSubcategoryDropdown(false)
                    setShowCountryDropdown(false)
                  }}
                  className="w-full flex items-center justify-between rounded-lg border border-(--line) px-4 py-2.5 text-left text-(--sea-ink) hover:border-(--palm) focus:border-(--palm) focus:outline-none transition"
                >
                  <span className={formData.city ? 'text-(--sea-ink)' : 'text-(--sea-ink-soft)'}>
                    {formData.city || 'Выберите город'}
                  </span>
                  <ChevronDown className="size-4 text-(--sea-ink-soft)" />
                </button>

                {showCityDropdown && filterConfig && (
                  <div className="absolute z-50 mt-1 w-full rounded-lg border border-(--line) bg-white shadow-lg max-h-64 overflow-y-auto">
                    <button
                      type="button"
                      onClick={() => {
                        setUseCustomCity(true)
                        setShowCityDropdown(false)
                      }}
                      className="w-full px-4 py-2.5 text-left text-sm text-(--palm) hover:bg-(--link-bg-hover) transition border-b border-(--line)"
                    >
                      + Ввести город вручную
                    </button>

                    {filterConfig.default_cities.length > 0 && (
                      <div>
                        <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50 sticky top-0">
                          Популярные города
                        </div>
                        {filterConfig.default_cities.map((city) => (
                          <button
                            key={city}
                            type="button"
                            onClick={() => {
                              setFormData({ ...formData, city })
                              setShowCityDropdown(false)
                            }}
                            className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                              formData.city === city
                                ? 'bg-(--palm)/10 text-(--palm) font-medium'
                                : 'text-(--sea-ink)'
                            }`}
                          >
                            {city}
                          </button>
                        ))}
                      </div>
                    )}

                    {currentCountry && currentCountry.cities.length > 0 && (
                      <div>
                        <div className="px-4 py-2 text-xs font-semibold text-(--sea-ink-soft) bg-gray-50 sticky top-0">
                          {currentCountry.flag} {currentCountry.name}
                        </div>
                        {currentCountry.cities
                          .filter(city => !filterConfig!.default_cities.includes(city))
                          .map((city) => (
                            <button
                              key={city}
                              type="button"
                              onClick={() => {
                                setFormData({ ...formData, city })
                                setShowCityDropdown(false)
                              }}
                              className={`w-full px-4 py-2.5 text-left text-sm hover:bg-(--link-bg-hover) transition ${
                                formData.city === city
                                  ? 'bg-(--palm)/10 text-(--palm) font-medium'
                                  : 'text-(--sea-ink)'
                              }`}
                            >
                              {city}
                            </button>
                          ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
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
              className="w-full rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
            >
              <option value="">Выберите состояние</option>
              {filterConfig?.conditions.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Size */}
          {needsSize && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-(--sea-ink)">
                Размер
              </label>
              <input
                type="text"
                value={formData.size}
                onChange={(e) => setFormData({ ...formData, size: e.target.value })}
                className="w-full rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition"
                placeholder="M, L, 48, 50..."
              />
            </div>
          )}

          {/* Description */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-(--sea-ink)">
              Описание
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={5}
              className="w-full rounded-lg border border-(--line) px-4 py-2.5 text-(--sea-ink) focus:border-(--palm) focus:outline-none transition resize-none"
              placeholder="Расскажите подробнее о товаре..."
            />
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            {saved ? (
              <button
                type="button"
                onClick={() => submitMut.mutate()}
                disabled={submitMut.isPending}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-500 py-3 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50 transition"
              >
                {submitMut.isPending ? 'Отправка...' : 'Отправить на модерацию'}
              </button>
            ) : (
              <button
                type="submit"
                disabled={updateMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-(--palm) py-3 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50 transition"
              >
                <Save className="size-4" />
                {updateMutation.isPending ? 'Сохранение...' : 'Сохранить изменения'}
              </button>
            )}
            <Link
              to="/my-ads"
              className="flex items-center justify-center rounded-lg border border-(--line) px-6 py-3 text-sm font-medium text-(--sea-ink) hover:bg-(--link-bg-hover)"
            >
              Отмена
            </Link>
          </div>

          <p className="text-center text-xs text-(--sea-ink-soft)">
            {saved
              ? 'Изменения сохранены. Отправьте на модерацию когда будете готовы.'
              : 'После сохранения будет доступна кнопка отправки на модерацию'}
          </p>
        </form>
      </div>
    </div>
  )
}
