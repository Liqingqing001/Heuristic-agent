<script setup>
import { ref, onMounted } from 'vue'
import { getKnowledgeStats, ingestKnowledge } from '../api.js'

const stats = ref(null)
const ingesting = ref(false)
const message = ref('')
const error = ref('')

const LABELS = { lecture: '讲义', solutions: '题解', buglib: 'Bug 库' }

async function load() {
  try {
    stats.value = await getKnowledgeStats()
  } catch (e) {
    error.value = '加载失败：' + e.message
  }
}

async function ingest() {
  ingesting.value = true
  error.value = ''
  message.value = '建库中，首次需下载 BGE 模型，请耐心等待…'
  try {
    const res = await ingestKnowledge()
    if (res.status === 'ok') {
      message.value = '建库完成'
      await load()
    } else {
      message.value = ''
      error.value = res.message || '建库失败'
    }
  } catch (e) {
    message.value = ''
    error.value = '建库请求失败：' + e.message
  } finally {
    ingesting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="kb-panel">
    <h3>知识库状态</h3>
    <table v-if="stats">
      <tr v-for="(label, key) in LABELS" :key="key">
        <td>{{ label }}</td>
        <td>{{ stats[key] ?? 0 }} 条</td>
      </tr>
    </table>
    <p v-else-if="!error" class="empty-hint">尚未加载</p>

    <button :disabled="ingesting" @click="ingest">
      {{ ingesting ? '建库中…' : '重新建库' }}
    </button>
    <p v-if="message">{{ message }}</p>
    <p v-if="error" class="error-text">{{ error }}</p>
  </div>
</template>
