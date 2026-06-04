// frontend/src/composables/useLocale.js
import { ref } from 'vue'
import zh from '../locales/zh.js'
import en from '../locales/en.js'

const MAPS = { zh, en }
const locale = ref(localStorage.getItem('mirofish_locale') || 'zh')

export function useLocale() {
  const t = (key) => MAPS[locale.value]?.[key] ?? key
  const setLocale = (lang) => {
    locale.value = lang
    localStorage.setItem('mirofish_locale', lang)
  }
  return { locale, t, setLocale }
}
