<template>
  <div v-if="usage" class="usage-counter">
    <span class="usage-item">{{ t('usage.tokens') }}: {{ usage.total_tokens.toLocaleString() }}</span>
    <span class="usage-sep">|</span>
    <span class="usage-item">{{ t('usage.cost') }}: ${{ usage.estimated_cost_usd }}</span>
    <span class="usage-sep">|</span>
    <span class="usage-item">{{ t('usage.calls') }}: {{ usage.call_count }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useLocale } from '../composables/useLocale.js'

const props = defineProps({
  projectId: { type: String, default: null },
  active: { type: Boolean, default: true },
})

const { t } = useLocale()
const usage = ref(null)
let timer = null

async function fetchUsage() {
  if (!props.projectId) return
  try {
    const res = await fetch(`/api/usage/${props.projectId}`)
    const json = await res.json()
    if (json.success) usage.value = json.data
  } catch { /* ignore — counter shows nothing on failure */ }
}

function start() {
  fetchUsage()
  timer = setInterval(fetchUsage, 3000)
}

function stop() {
  clearInterval(timer)
  timer = null
}

onMounted(() => { if (props.active && props.projectId) start() })
onUnmounted(() => stop())

watch(() => [props.active, props.projectId], ([active, pid]) => {
  stop()
  if (active && pid) start()
})
</script>

<style scoped>
.usage-counter {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #666;
  padding: 6px 12px;
  background: #f5f5f5;
  border: 1px solid #e5e5e5;
}
.usage-sep { color: #ccc; }
.usage-item { white-space: nowrap; }
</style>
