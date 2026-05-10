import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { AppLanguage, LANGUAGE_LOCALES } from './index'

export function getLocale(language: string): string {
  const appLanguage = language.split('-')[0] as AppLanguage
  return LANGUAGE_LOCALES[appLanguage] ?? LANGUAGE_LOCALES.uk
}

export function formatDateTime(
  value: string | number | Date | null | undefined,
  language: string,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }
): string {
  if (!value) return '-'
  try {
    return new Intl.DateTimeFormat(getLocale(language), options).format(new Date(value))
  } catch {
    return String(value)
  }
}

export function useLocaleFormatters() {
  const { i18n } = useTranslation()

  return useMemo(
    () => ({
      locale: getLocale(i18n.language),
      formatDateTime: (
        value: string | number | Date | null | undefined,
        options?: Intl.DateTimeFormatOptions
      ) => formatDateTime(value, i18n.language, options),
    }),
    [i18n.language]
  )
}
