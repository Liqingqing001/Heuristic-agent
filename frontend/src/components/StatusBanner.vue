<script setup>
import { computed, ref } from 'vue'
import { state } from '../session.js'
const props = defineProps({ status: { type: Object, default: null } })
defineEmits(['open-settings', 'retry'])
const expanded = ref(false)
const total = computed(() =>
  Object.values(props.status?.knowledge || {}).reduce(
    (sum, n) => sum + (Number(n) || 0),
    0
  )
)
const level = computed(() =>
  !props.status
    ? 'loading'
    : props.status.unavailable
      ? 'warn'
      : !state.llmKey && !props.status.server_key
        ? 'setup'
        : props.status.knowledge_error || !total.value
          ? 'warn'
          : 'ok'
)
const label = computed(
  () =>
    ({
      loading: '正在检查服务状态',
      setup: '开始前，连接你的 AI 助教',
      warn: '部分服务需要检查',
      ok: '助教已就绪',
    })[level.value]
)
</script>
<template>
  <div class="status-strip" :class="level">
    <div class="status-main">
      <span class="status-dot"></span><strong>{{ label }}</strong
      ><span v-if="level === 'setup'" class="status-summary"
        >配置个人密钥后，就能提问和诊断代码</span
      ><span v-else-if="level === 'ok'" class="status-summary"
        >随时开始你的下一次思考</span
      >
    </div>
    <div class="status-actions">
      <button v-if="level === 'setup'" @click="$emit('open-settings')">
        配置密钥 →</button
      ><button v-else-if="status?.unavailable" @click="$emit('retry')">
        重新检查</button
      ><button v-else :aria-expanded="expanded" @click="expanded = !expanded">
        {{ expanded ? '收起' : '查看状态' }}
      </button>
    </div>
    <p v-if="expanded" class="status-detail">
      {{
        status?.knowledge_error
          ? '知识库暂不可用，可请教师检查或重建。'
          : `已索引 ${total} 个知识片段。`
      }}
      模型：{{ status?.model || '等待检查' }}。{{
        state.llmKey
          ? '使用个人密钥。'
          : status?.server_key
            ? '使用服务端密钥。'
            : '尚未配置个人密钥。'
      }}
      <button @click="$emit('open-settings')">模型设置</button>
    </p>
  </div>
</template>
<style scoped>
.status-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 13px 17px;
  margin-bottom: 22px;
  font-size: 12px;
}
.status-main {
  display: flex;
  align-items: center;
  gap: 10px;
}
.status-main strong {
  font-size: 12px;
  font-weight: 550;
}
.status-summary {
  color: var(--muted);
}
.status-dot {
  height: 7px;
  width: 7px;
  background: #2c9c79;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-strip.setup {
  background: #f0f5ff;
  border-color: #dce6ff;
}
.setup .status-dot {
  background: var(--primary);
}
.warn .status-dot {
  background: #d97706;
}
.loading .status-dot {
  background: #94a3b8;
}
.status-actions button,
.status-detail button {
  border: 0;
  background: none;
  color: var(--primary);
  font-size: 12px;
  padding: 3px;
}
.status-detail {
  flex-basis: 100%;
  margin: 0;
  line-height: 1.7;
  color: var(--muted);
}
@media (max-width: 760px) {
  .status-summary {
    display: none;
  }
  .status-strip {
    padding: 12px;
    margin-bottom: 18px;
  }
}
</style>
