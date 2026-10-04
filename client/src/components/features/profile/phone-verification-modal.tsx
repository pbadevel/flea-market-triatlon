// src/components/features/profile/phone-verification-modal.tsx
import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Phone, ShieldCheck, X } from 'lucide-react'
import { sendPhoneCode, verifyPhoneCode } from '@/lib/api/client/phoneVerification'
import { PhoneInput } from '@/components/ui/phone-input'
import { normalizePhone, isValidPhone, formatPhone } from '@/lib/utils'

export function PhoneVerificationModal({
  token,
  initialPhone,
  onClose,
}: {
  token: string
  initialPhone?: string | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  // initialPhone уже может быть в формате E.164 — форматируем для отображения
  const [phone, setPhone] = useState(
    initialPhone ? formatPhone(initialPhone) : '',
  )
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [resendIn, setResendIn] = useState(0)

  useEffect(() => {
    if (resendIn <= 0) return
    const t = setTimeout(() => setResendIn((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [resendIn])

  const sendMutation = useMutation({
    mutationFn: () => {
      // ─── На бэкенд отправляем ЧИСТЫЙ E.164 ───
      const clean = normalizePhone(phone)
      return sendPhoneCode(token, clean)
    },
    onSuccess: () => {
      setError('')
      setCode('')
      setStep('code')
      setResendIn(60)
    },
    onError: (err: any) => setError(err.message || 'Не удалось отправить код'),
  })

  const verifyMutation = useMutation({
    mutationFn: () => {
      const clean = normalizePhone(phone)
      return verifyPhoneCode(token, clean, code)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      onClose()
    },
    onError: (err: any) => setError(err.message || 'Неверный код'),
  })

  const handleSend = () => {
    setError('')
    sendMutation.mutate()
  }

  const handleVerify = () => {
    setError('')
    verifyMutation.mutate()
  }

  const isPhoneValid = isValidPhone(phone)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl border border-(--line) bg-(--surface-strong) p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-lg font-bold text-(--sea-ink)">
            <ShieldCheck className="size-5 text-(--palm)" />
            Подтверждение телефона
          </h3>
          <button
            onClick={onClose}
            className="rounded p-1 text-(--sea-ink-soft) hover:bg-(--link-bg-hover)"
          >
            <X className="size-5" />
          </button>
        </div>

        {step === 'phone' ? (
          <div className="space-y-4">
            <PhoneInput
              value={phone}
              onChange={setPhone}
              label="Номер телефона"
              error={
                phone && !isPhoneValid ? 'Введите корректный российский номер' : undefined
              }
            />
            <p className="text-xs text-(--sea-ink-soft)">
              Номер обязателен для размещения объявлений. Мы отправим SMS с кодом
              подтверждения.
            </p>

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleSend}
              disabled={sendMutation.isPending || !isPhoneValid}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-(--palm) px-6 py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
            >
              <Phone className="size-4" />
              {sendMutation.isPending ? 'Отправка...' : 'Отправить код'}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-(--sea-ink-soft)">
              Введите 6-значный код, отправленный на номер{' '}
              <span className="font-medium text-(--sea-ink)">{phone}</span>
            </p>

            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="••••••"
              autoFocus
              className="w-full rounded-xl border border-(--line) px-4 py-3 text-center text-2xl font-bold tracking-[0.5em] text-(--sea-ink) focus:border-(--palm) focus:outline-none"
            />

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
                {error}
              </div>
            )}

            <button
              onClick={handleVerify}
              disabled={verifyMutation.isPending || code.length !== 6}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-(--palm) px-6 py-2.5 text-sm font-medium text-white hover:bg-(--palm)/90 disabled:opacity-50"
            >
              <ShieldCheck className="size-4" />
              {verifyMutation.isPending ? 'Проверка...' : 'Подтвердить'}
            </button>

            <div className="flex items-center justify-between text-sm">
              <button
                onClick={() => {
                  setStep('phone')
                  setError('')
                }}
                className="text-(--sea-ink-soft) hover:text-(--sea-ink)"
              >
                Изменить номер
              </button>

              {resendIn > 0 ? (
                <span className="text-(--sea-ink-soft)">Повторно через {resendIn} с</span>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={sendMutation.isPending || !isPhoneValid}
                  className="text-(--palm) hover:underline disabled:opacity-50"
                >
                  Отправить код повторно
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}