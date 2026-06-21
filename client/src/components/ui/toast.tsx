import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Info } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  type: ToastType
}

let nextId = 0
let listeners: Array<(toasts: Toast[]) => void> = []
let toasts: Toast[] = []

function notify(message: string, type: ToastType) {
  const id = nextId++
  toasts = [...toasts, { id, message, type }]
  listeners.forEach((l) => l(toasts))
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    listeners.forEach((l) => l(toasts))
  }, 3000)
}

export const toast = {
  success: (msg: string) => notify(msg, 'success'),
  error: (msg: string) => notify(msg, 'error'),
  info: (msg: string) => notify(msg, 'info'),
}

export function ToastContainer() {
  const [items, setItems] = useState<Toast[]>([])

  useEffect(() => {
    listeners.push(setItems)
    return () => {
      listeners = listeners.filter((l) => l !== setItems)
    }
  }, [])

  if (!items.length) return null

  const iconMap = {
    success: <CheckCircle className="size-5 text-green-500" />,
    error: <XCircle className="size-5 text-red-500" />,
    info: <Info className="size-5 text-blue-500" />,
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className="flex items-center gap-3 rounded-lg border border-(--line) bg-white px-4 py-3 shadow-lg transition-all duration-300"
          style={{ animation: 'toast-in 0.3s ease-out' }}
        >
          {iconMap[t.type]}
          <span className="text-sm text-(--sea-ink)">{t.message}</span>
        </div>
      ))}
    </div>
  )
}
