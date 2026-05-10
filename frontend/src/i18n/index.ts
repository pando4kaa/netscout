import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en'
import uk from './locales/uk'

export const LANGUAGE_STORAGE_KEY = 'netscout_language'
export const SUPPORTED_LANGUAGES = ['uk', 'en'] as const
export type AppLanguage = (typeof SUPPORTED_LANGUAGES)[number]

export const LANGUAGE_LABELS: Record<AppLanguage, string> = {
  uk: 'UA',
  en: 'EN',
}

export const LANGUAGE_LOCALES: Record<AppLanguage, string> = {
  uk: 'uk-UA',
  en: 'en-US',
}

const resources = {
  uk: { translation: uk },
  en: { translation: en },
} as const

function isSupportedLanguage(value: string | null | undefined): value is AppLanguage {
  return SUPPORTED_LANGUAGES.includes(value as AppLanguage)
}

function normalizeLanguage(value: string | null | undefined): AppLanguage | null {
  if (!value) return null
  const lang = value.toLowerCase().split('-')[0]
  return isSupportedLanguage(lang) ? lang : null
}

export function getInitialLanguage(): AppLanguage {
  const stored = normalizeLanguage(localStorage.getItem(LANGUAGE_STORAGE_KEY))
  if (stored) return stored

  const browserLanguage = normalizeLanguage(navigator.language)
  return browserLanguage ?? 'uk'
}

void i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES,
    interpolation: {
      escapeValue: false,
    },
  })

i18n.on('languageChanged', (language) => {
  const normalized = normalizeLanguage(language) ?? 'uk'
  document.documentElement.lang = normalized
  localStorage.setItem(LANGUAGE_STORAGE_KEY, normalized)
})

document.documentElement.lang = getInitialLanguage()

export default i18n
