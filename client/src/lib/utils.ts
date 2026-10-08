import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}


/**
 * Нормализация номера к E.164: +79991234567
 * Используется перед отправкой на бэкенд.
 */
export function normalizePhone(raw: string): string {
  const digits = raw.replace(/\D/g, '')

  if (digits.length === 11 && digits.startsWith('8')) {
    return `+7${digits.slice(1)}`
  }
  if (digits.length === 11 && digits.startsWith('7')) {
    return `+${digits}`
  }
  if (digits.length === 10 && digits.startsWith('9')) {
    return `+7${digits}`
  }
  if (digits.length === 11 && digits.startsWith('7')) {
    return `+${digits}`
  }

  // Если не получилось нормализовать — возвращаем как есть (бэкенд валидирует)
  return raw.replace(/\D/g, '').length === 11 ? `+${raw.replace(/\D/g, '')}` : raw
}

/**
 * Форматирование для отображения: +7 (999) 123-45-67
 * Применяется при каждом изменении инпута.
 */
export function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '')

  // Если пусто — возвращаем пусто
  if (digits.length === 0) return ''

  // Нормализуем: приводим к формату 7XXXXXXXXXX
  let normalized = digits
  if (normalized.startsWith('8') && normalized.length === 11) {
    normalized = '7' + normalized.slice(1)
  }
  if (!normalized.startsWith('7')) {
    normalized = '7' + normalized
  }

  // Берём максимум 11 цифр
  normalized = normalized.slice(0, 11)

  // Постепенно строим маску
  const [, d1, d2, d3, d4, d5, d6, d7, d8, d9, d10] = normalized.split('')

  let result = '+7'
  if (d1) result += ` (${d1}`
  if (d2) result += d2
  if (d3) result += d3
  if (d3) result += ')'
  if (d4) result += ` ${d4}`
  if (d5) result += d5
  if (d6) result += d6
  if (d6) result += '-'
  if (d7) result += d7
  if (d8) result += d8
  if (d8) result += '-'
  if (d9) result += d9
  if (d10) result += d10

  return result
}

/**
 * Валидация российского номера
 */
export function isValidPhone(phone: string): boolean {
  const normalized = normalizePhone(phone)
  return /^\+7\d{10}$/.test(normalized)
}