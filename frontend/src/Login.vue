<script setup>
import { ref } from 'vue'
import { apiLogin, apiRegister } from './api.js'

const emit = defineEmits(['success'])

const mode = ref('login')  // 'login' | 'register'
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  const u = username.value.trim()
  const p = password.value
  if (!u || !p) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await apiLogin(u, p)
    } else {
      await apiRegister(u, p)
    }
    emit('success')
  } catch (e) {
    error.value = e.message || '操作失败'
  } finally {
    loading.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<template>
    <div class="login-wrap">
        <div class="login-card">
            <h1>{{ mode === 'login' ? '登录' : '注册' }} 智育助教</h1>
            <p class="sub">基于 RAG 与苏格拉底教学法的数据结构智能助教</p>

            <input v-model="username" placeholder="用户名" @keydown.enter="submit" />
            <input v-model="password" type="password" placeholder="密码（至少6位）" @keydown.enter="submit" />

            <div v-if="error" class="err">{{ error }}</div>

            <button :disabled="loading" @click="submit">
                {{ loading ? '处理中…' : (mode === 'login' ? '登录' : '注册') }}
            </button>

            <div class="switch">
                {{ mode === 'login' ? '还没有账号？' : '已有账号？' }}
                <a @click="switchMode">{{ mode === 'login' ? '去注册' : '去登录' }}</a>
            </div>
        </div>
    </div>
</template>

<style scoped>
    .login-wrap {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #eef4ff 0%, #dbeafe 100%);
    }

    .login-card {
        width: 360px;
        background: white;
        border-radius: 16px;
        padding: 36px 32px;
        box-shadow: 0 20px 60px rgba(59, 130, 246, 0.15);
        text-align: center;
    }

    h1 {
        color: #3b82f6;
        margin: 0 0 6px;
    }

    .sub {
        font-size: 12px;
        color: #94a3b8;
        margin: 0 0 24px;
    }

    input {
        width: 100%;
        padding: 12px 14px;
        margin-bottom: 12px;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        font-size: 14px;
        box-sizing: border-box;
    }

        input:focus {
            border-color: #3b82f6;
            outline: none;
        }

    button {
        width: 100%;
        padding: 12px;
        border: none;
        border-radius: 8px;
        background: #3b82f6;
        color: white;
        font-size: 15px;
        cursor: pointer;
        margin-top: 8px;
    }

        button:hover:not(:disabled) {
            background: #2563eb;
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

    .err {
        color: #ef4444;
        font-size: 13px;
        margin-bottom: 8px;
    }

    .switch {
        font-size: 13px;
        color: #64748b;
        margin-top: 20px;
    }

        .switch a {
            color: #3b82f6;
            cursor: pointer;
            margin-left: 4px;
        }
</style>