<template>
  <router-view />
  <button class="locale-toggle" @click="setLocale(locale === 'zh' ? 'en' : 'zh')">
    {{ locale === 'zh' ? 'EN' : 'ZH' }}
  </button>
</template>

<script setup>
import { useLocale } from './composables/useLocale.js'
const { locale, setLocale } = useLocale()
</script>

<style>
/* Global style reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #000000;
  background-color: #ffffff;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f1f1; }
::-webkit-scrollbar-thumb { background: #000000; }
::-webkit-scrollbar-thumb:hover { background: #333333; }
button { font-family: inherit; }

.locale-toggle {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  width: 40px;
  height: 40px;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  transition: all 0.2s;
}
.locale-toggle:hover {
  background: #000;
  color: #fff;
  border-color: #000;
}
</style>
