// Server-side API proxy – hides backend domain from client
import { createServerFn } from '@tanstack/react-start'

const API_HOST = 'http://127.0.0.1:8001'

export class BannedError extends Error {
  constructor(message = 'Аккаунт заблокирован') {
    super(message)
    this.name = 'BannedError'
  }
}

function handleErrorResponse(res: Response, err: any) {
  if (res.status === 403 && err?.code === 'BANNED') {
    throw new BannedError(err.detail)
  }
  const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
  throw new Error(detail)
}

// Generic API proxy for JSON requests
export const serverApi = createServerFn({ method: 'POST' })
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
      handleErrorResponse(res, err)
    }

    return await res.json()
  })

// Form-data upload proxy (create/update ad with photos)
export const serverUpload = createServerFn({ method: 'POST' })
  .inputValidator((data: {
    path: string
    token: string
    method?: string
    fields: Record<string, string[]>
    fileNames: string[]
    fileBases: string[]
    fileTypes: string[]
  }) => data)
  .handler(async ({ data }) => {
    const url = `${API_HOST}/v1${data.path}`
    const formData = new FormData()
    
    for (const [key, vals] of Object.entries(data.fields)) {
      for (const val of vals) {
        formData.append(key, val)
      }
    }
    for (let i = 0; i < data.fileNames.length; i++) {
      const buf = Buffer.from(data.fileBases[i], 'base64')
      const type = data.fileTypes[i] || 'application/octet-stream'
      formData.append('photos', new Blob([buf], { type }), data.fileNames[i])
    }

    const res = await fetch(url, {
      method: data.method || 'POST',
      headers: { Authorization: `Bearer ${data.token}` },
      body: formData,
    })

    if (!res.ok) {
      if (res.status === 413) {
        throw new Error('Файлы слишком большие. Максимальный размер — 50 МБ.')
      }
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
      handleErrorResponse(res, err)
    }
    return await res.json()
  })
