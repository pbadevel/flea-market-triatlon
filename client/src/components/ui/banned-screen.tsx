import { Ban } from 'lucide-react'

export function BannedScreen({ message }: { message?: string }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-(--bg-base) p-4">
      <div className="w-full max-w-md rounded-2xl border border-(--line) bg-white p-8 text-center shadow-lg">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
          <Ban className="size-8 text-red-500" />
        </div>
        <h1 className="text-xl font-bold text-(--sea-ink) mb-2">
          Аккаунт заблокирован
        </h1>
        <p className="text-sm text-(--sea-ink-soft) mb-6">
          {message || 'Ваш аккаунт был заблокирован администратором. Если вы считаете, что это ошибка, обратитесь в поддержку.'}
        </p>
        <a
          href="/"
          className="inline-block rounded-lg bg-(--palm) px-6 py-2.5 text-sm font-medium text-white hover:opacity-90 transition"
        >
          На главную
        </a>
      </div>
    </div>
  )
}
