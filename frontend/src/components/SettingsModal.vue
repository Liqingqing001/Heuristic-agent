<script setup>
import { ref, watch } from 'vue'
import { state, saveLlmKey, clearLlmKey } from '../session.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  serverKey: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const key = ref('')
const remember = ref(false)
const saved = ref(false)
const visible = ref(false)

watch(
  () => props.open,
  (open) => {
    if (open) {
      key.value = state.llmKey
      remember.value = state.remember
      saved.value = false
    }
  }
)

function save() {
  saveLlmKey(key.value, remember.value)
  saved.value = true
  setTimeout(() => {
    saved.value = false
    emit('close')
  }, 500)
}

function clear() {
  clearLlmKey()
  key.value = ''
  remember.value = false
  saved.value = true
}
</script>

<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <div class="modal" v-dialog="() => emit('close')">
      <h3>模型设置（自带密钥）</h3>
      <p class="tip">
        这里的 key 只保存在你自己的浏览器里（默认仅本次会话，勾选后记住本机），
        请求时通过后端透传给
        DeepSeek，<strong>不会写进数据库，也不会出现在日志里</strong>。
      </p>

      <label class="label" for="llm-key">DeepSeek API Key</label>
      <input
        id="llm-key"
        v-model="key"
        :type="visible ? 'text' : 'password'"
        placeholder="sk-..."
        autocomplete="off"
        spellcheck="false"
      />

      <button
        class="ghost reveal-key"
        :aria-pressed="visible"
        @click="visible = !visible"
      >
        {{ visible ? '隐藏密钥' : '显示密钥' }}
      </button>
      <label class="remember">
        <input v-model="remember" type="checkbox" />
        记住本机（慎用公共电脑）
      </label>

      <p class="hint">
        没有密钥？去
        <a
          href="https://platform.deepseek.com/api_keys"
          target="_blank"
          rel="noreferrer"
          >DeepSeek 开放平台</a
        >
        注册并创建。{{
          serverKey
            ? '当前服务端也配置了公共密钥，不填也能用，但会消耗服务端的额度。'
            : '本项目不提供公共密钥，必须自备。'
        }}
      </p>

      <div class="actions">
        <button class="ghost" @click="clear">清除</button>
        <button class="ghost" @click="emit('close')">取消</button>
        <button class="primary" @click="save">
          {{ saved ? '已保存' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reveal-key {
  margin-top: 8px;
  font-size: 12px;
}
.mask {
  padding: 16px;
}
.modal {
  max-width: 100%;
  max-height: 86dvh;
  overflow-y: auto;
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal {
  width: 460px;
  background: white;
  border-radius: 14px;
  padding: 24px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
}

h3 {
  margin: 0 0 10px;
  color: #1e293b;
}

.tip {
  font-size: 12px;
  color: #64748b;
  line-height: 1.7;
  margin: 0 0 18px;
}

.label {
  display: block;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}

input:not([type='checkbox']) {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  box-sizing: border-box;
  font-family: monospace;
}

input:not([type='checkbox']):focus {
  border-color: var(--primary);
  outline: none;
}

.remember {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin-top: 12px;
}

.hint {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.7;
  margin: 16px 0 0;
}

.hint a {
  color: var(--primary);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

button {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}

.ghost {
  background: white;
  border-color: #e2e8f0;
  color: #475569;
}

.primary {
  background: var(--primary);
  color: white;
}

.primary:hover {
  background: var(--primary);
}
</style>
