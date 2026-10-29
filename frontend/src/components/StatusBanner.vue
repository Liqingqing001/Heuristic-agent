<script setup>
import { computed } from 'vue'
import { state } from '../session.js'

const props = defineProps({
  status: { type: Object, default: null },
})

const emit = defineEmits(['open-settings'])

const knowledgeTotal = computed(() => {
  const knowledge = props.status?.knowledge || {}
  return Object.values(knowledge).reduce((sum, value) => sum + (Number(value) || 0), 0)
})

const keyMode = computed(() => {
  if (state.llmKey) return '个人密钥'
  if (props.status?.server_key) return '服务端密钥'
  return '未配置'
})

const level = computed(() => {
  if (!state.llmKey && !props.status?.server_key) return 'error'
  if (props.status?.knowledge_error) return 'warn'
  if (!knowledgeTotal.value) return 'warn'
  return 'ok'
})

const message = computed(() => {
  if (level.value === 'error') return '还没有可用的模型密钥：点右侧「模型设置」填入你自己的 API Key 才能对话'
  if (props.status?.knowledge_error) return `知识库不可用（${props.status.knowledge_error}），对话与诊断仍可进行`
  if (!knowledgeTotal.value) return '知识库还没建库：教师可在「知识库」页点一次「重新建库」'
  return `就绪 · 知识库 ${knowledgeTotal.value} 块 · 模型 ${props.status?.model || 'deepseek-chat'}（${keyMode.value}）`
})
</script>

<template>
  <div class="banner" :class="level">
    <span class="dot"></span>
    <span class="text">{{ message }}</span>
    <button class="action" @click="emit('open-settings')">
      {{ level === 'error' ? '填写密钥' : '模型设置' }}
    </button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-radius: 10px;
  font-size: 13px;
  margin-bottom: 16px;
  border: 1px solid transparent;
}

.banner.ok {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #15803d;
}

.banner.warn {
  background: #fffbeb;
  border-color: #fde68a;
  color: #b45309;
}

.banner.error {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.text {
  flex: 1;
  line-height: 1.5;
}

.action {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
</style>
