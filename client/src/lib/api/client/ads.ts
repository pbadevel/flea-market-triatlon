import { serverApi, serverUpload } from '../server-proxy'
import type { AdFilters, MyAd } from '@/types/ad'

// Helper: read FormData files into base64 + fields
async function formDataToUploadPayload(fd: FormData) {
  const fields: Record<string, string> = {}
  const fileNames: string[] = []
  const fileBases: string[] = []

  for (const [key, val] of fd.entries()) {
    if (val instanceof File) {
      const buf = await val.arrayBuffer()
      fileBases.push(Buffer.from(buf).toString('base64'))
      fileNames.push(val.name)
    } else {
      fields[key] = String(val)
    }
  }
  return { fields, fileNames, fileBases }
}

export const fetchAds = (filters: AdFilters = {}) => {
  const params = new URLSearchParams()
  if (filters.page) params.set('page', String(filters.page))
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.category) params.set('category', filters.category)
  if (filters.search) params.set('search', filters.search)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.country) params.set('country', filters.country)
  if (filters.city) params.set('city', filters.city)
  if (filters.min_price) params.set('min_price', String(filters.min_price))
  if (filters.max_price) params.set('max_price', String(filters.max_price))
  if (filters.condition) params.set('condition', filters.condition)
  if (filters.subcategory) params.set('subcategory', filters.subcategory)
  if (filters.ad_type) params.set('ad_type', filters.ad_type)
  return serverApi({ data: { path: `/ads?${params.toString()}` } })
}

export const fetchProduct = (productId: string | number) =>
  serverApi({ data: { path: `/products/${productId}` } })

export const fetchFilters = () =>
  serverApi({ data: { path: '/filters' } })

export const fetchMyAds = (token: string) =>
  serverApi({ data: { path: '/ads/my', token } })

export const createAd = async ({ token, formData }: { token: string; formData: FormData }) => {
  const payload = await formDataToUploadPayload(formData)
  return serverUpload({ data: { ...payload, path: '/ads', method: 'POST', token } })
}

export const updateAd = async ({ token, adId, formData }: { token: string; adId: number; formData: FormData }) => {
  const payload = await formDataToUploadPayload(formData)
  return serverUpload({ data: { ...payload, path: `/ads/${adId}`, method: 'PUT', token } })
}

export const deleteAd = (token: string, adId: number) =>
  serverApi({ data: { path: `/ads/${adId}`, method: 'DELETE', token } })

export const resendAd = (token: string, adId: number) =>
  serverApi({ data: { path: `/ads/${adId}/resend`, method: 'POST', token } })
