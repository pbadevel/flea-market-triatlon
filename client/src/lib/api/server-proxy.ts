// Server-side API proxy – hides backend domain from client
import { createServerFn } from '@tanstack/react-start'
import { BASE_URL } from './endpoints'

const API_HOST = `${BASE_URL}`

// Generic API proxy for JSON requests
export const serverApi = createServerFn()
  .inputValidator((data: {
    path: string
    method?: string
    body?: unknown
    token?: string
  }) => data)
  .handler(async ({ data }) => {
    const url = `${API_HOST}/v1${data.path}`
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (data.token) {
      headers['Authorization'] = `Bearer ${data.token}`
    }

    const res = await fetch(url, {
      method: data.method || 'GET',
      headers,
      body: data.body ? JSON.stringify(data.body) : undefined,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      throw new Error(detail)
    }

    return await res.json()
  })

// Form-data upload proxy (create/update ad with photos)
export const serverUpload = createServerFn()
  .inputValidator((data: {
    path: string
    token: string
    method?: string
    fields: Record<string, string>
    fileNames: string[]
    fileBases: string[]
  }) => data)
  .handler(async ({ data }) => {
    const url = `${API_HOST}/v1${data.path}`
    const formData = new FormData()
    
    for (const [key, val] of Object.entries(data.fields)) {
      formData.append(key, val)
    }
    for (let i = 0; i < data.fileNames.length; i++) {
      const buf = Buffer.from(data.fileBases[i], 'base64')
      formData.append('photos', new Blob([buf]), data.fileNames[i])
    }

    const res = await fetch(url, {
      method: data.method || 'POST',
      headers: { Authorization: `Bearer ${data.token}` },
      body: formData,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
      const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      throw new Error(detail)
    }
    return await res.json()
  })
