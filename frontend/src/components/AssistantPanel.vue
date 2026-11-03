<script setup>
import { computed, defineAsyncComponent } from 'vue'
const ChatPanel = defineAsyncComponent(() => import('./ChatPanel.vue'))
const CodeAnalyze = defineAsyncComponent(() => import('./CodeAnalyze.vue'))
import AppIcon from './AppIcon.vue'
import { setAssistantMode, state } from '../session.js'

const mode = computed(() => state.assistantMode)
const current = computed(() =>
  mode.value === 'code' ? CodeAnalyze : ChatPanel
)
</script>

<template>
  <div class="assistant">
    <div class="mode-bar">
      <button
        :class="{ active: mode === 'chat' }"
        @click="setAssistantMode('chat')"
      >
        <AppIcon name="chat" :size="17" /> 对话提问
      </button>
      <button
        :class="{ active: mode === 'code' }"
        @click="setAssistantMode('code')"
      >
        <AppIcon name="code" :size="17" /> 代码诊断
      </button>
      <span class="hint">从一个问题开始，让理解更进一步</span>
    </div>

    <KeepAlive>
      <component :is="current" />
    </KeepAlive>
  </div>
</template>

<style scoped>
.assistant {
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}
.mode-bar button {
  display: flex;
  align-items: center;
  gap: 7px;
}
.mode-bar {
  flex-wrap: wrap;
}
.hint {
  line-height: 1.6;
}
@media (max-width: 760px) {
  .assistant {
    padding: 12px;
  }
  .hint {
    display: none;
  }
  .mode-bar button {
    padding: 9px 12px !important;
  }
}

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
  border-color: var(--primary);
  background: var(--primary);
  color: white;
}

.hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--muted);
}
</style>
