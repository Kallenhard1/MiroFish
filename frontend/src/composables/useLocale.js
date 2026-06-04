// frontend/src/composables/useLocale.js
import { ref } from 'vue'
import zh from '../locales/zh.js'
import en from '../locales/en.js'

const MAPS = { zh, en }
const SUPPORTED = Object.keys(MAPS)

function getSavedLocale() {
  try {
    return localStorage.getItem('mirofish_locale') || 'zh'
  } catch {
    return 'zh'
  }
}

const locale = ref(getSavedLocale())

export function useLocale() {
  const t = (key) => MAPS[locale.value]?.[key] ?? key
  const setLocale = (lang) => {
    if (!SUPPORTED.includes(lang)) return
    locale.value = lang
    try {
      localStorage.setItem('mirofish_locale', lang)
    } catch { /* private browsing */ }
  }
  return { locale, t, setLocale }
}
