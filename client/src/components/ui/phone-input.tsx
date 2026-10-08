// src/components/ui/phone-input.tsx
import { forwardRef, type InputHTMLAttributes } from 'react'
import { formatPhone } from '@/lib/utils'

interface PhoneInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string
  onChange: (value: string) => void
  error?: string
  label?: string
}

export const PhoneInput = forwardRef<HTMLInputElement, PhoneInputProps>(
  ({ value, onChange, error, label, className = '', ...rest }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value
      // Позволяем вводить пустую строку (очистка)
      if (raw === '') {
        onChange('')
        return
      }
      onChange(formatPhone(raw))
    }

    return (
      <div className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-(--sea-ink)">{label}</label>
        )}
        <input
          ref={ref}
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          value={value}
          onChange={handleChange}
          placeholder="+7 (___) ___-__-__"
          className={`w-full rounded-xl border px-4 py-2.5 text-(--sea-ink) focus:outline-none transition ${
            error
              ? 'border-red-300 focus:border-red-500'
              : 'border-(--line) focus:border-(--palm)'
          } ${className}`}
          {...rest}
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    )
  },
)

PhoneInput.displayName = 'PhoneInput'