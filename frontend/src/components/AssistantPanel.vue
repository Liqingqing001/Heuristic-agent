<script setup>
import { computed } from 'vue'
import ChatPanel from './ChatPanel.vue'
import CodeAnalyze from './CodeAnalyze.vue'
import { setAssistantMode, state } from '../session.js'

const mode = computed(() => state.assistantMode)
const current = computed(() => (mode.value === 'code' ? CodeAnalyze : ChatPanel))
</script>

<template>
  <div class="assistant">
    <div class="mode-bar">
      <button :class="{ active: mode === 'chat' }" @click="setAssistantMode('chat')">
        💬 对话提问
      </button>
      <button :class="{ active: mode === 'code' }" @click="setAssistantMode('code')">
        🧭 代码诊断
      </button>
      <span class="hint">两种模式共用同一套知识点与「只启发、不泄题」约束</span>
    </div>

    <KeepAlive>
      <component :is="current" />
    </KeepAlive>
  </div>
</template>

<style scoped>
.mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.mode-bar button {
  padding: 7px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
}

.mode-bar button.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: white;
}

.hint {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
}
</style>
