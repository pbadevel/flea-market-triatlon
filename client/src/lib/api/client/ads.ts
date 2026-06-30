import { serverApi, serverUpload } from '../server-proxy'
import type { AdFilters, MyAd } from '@/types/ad'

// Helper: read FormData files into base64 + fields
async function formDataToUploadPayload(fd: FormData) {
  const fields: Record<string, string[]> = {}
  const fileNames: string[] = []
  const fileBases: string[] = []
  const fileTypes: string[] = []

  const entries = Array.from(fd.entries())
  for (const [key, val] of entries) {
    if (val instanceof File) {
      const buf = await val.arrayBuffer()
      const bytes = new Uint8Array(buf)
      let binary = ''
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
      fileBases.push(btoa(binary))
      fileNames.push(val.name)
      fileTypes.push(val.type)
    } else {
      if (!fields[key]) fields[key] = []
      fields[key].push(String(val))
    }
  }
  return { fields, fileNames, fileBases, fileTypes }
}

export const fetchAds = (filters: AdFilters = {}) => {
  const params = new URLSearchParams()
  if (filters.page) params.set('page', String(filters.page))
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.categories?.length) filters.categories.forEach(c => params.append('category', c))
  if (filters.subcategories?.length) filters.subcategories.forEach(s => params.append('subcategory', s))
  if (filters.countries?.length) filters.countries.forEach(c => params.append('country', c))
  if (filters.cities?.length) filters.cities.forEach(c => params.append('city', c))
  if (filters.search) params.set('search', filters.search)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.minPrice) params.set('min_price', String(filters.minPrice))
  if (filters.maxPrice) params.set('max_price', String(filters.maxPrice))
  if (filters.condition) params.set('condition', filters.condition)
  if (filters.ad_type) params.set('ad_type', filters.ad_type)
  return serverApi({ data: { path: `/ads?${params.toString()}` } })
}

export const fetchProduct = (productId: string | number) =>
  serverApi({ data: { path: `/products/${productId}` } })

export const fetchFilters = () =>
  serverApi({ data: { path: '/filters' } })

export const fetchMyAds = (token: string) =>
  serverApi({ data: { path: '/ads/my', token } })

export const fetchAdForEdit = (token: string, adId: number) =>
  serverApi({ data: { path: `/ads/${adId}`, token } })

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

export const submitForModeration = (token: string, adId: number) =>
  serverApi({ data: { path: `/ads/${adId}/submit`, method: 'POST', token } })
