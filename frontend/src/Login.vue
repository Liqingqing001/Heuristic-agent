<script setup>
import { ref } from 'vue'
import { apiLogin, apiRegister } from './api.js'

const emit = defineEmits(['success'])

const mode = ref('login')  // 'login' | 'register'
const username = ref('')
const password = ref('')
const displayName = ref('')
const role = ref('student')
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
      await apiRegister(u, p, role.value, displayName.value.trim())
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

      <template v-if="mode === 'register'">
        <input v-model="displayName" placeholder="姓名 / 昵称（可选）" @keydown.enter="submit" />
        <div class="role-picker">
          <button
            type="button"
            class="role-btn"
            :class="{ active: role === 'student' }"
            @click="role = 'student'"
          >
            <strong>我是学生</strong>
            <span>加入班级、完成老师布置的任务</span>
          </button>
          <button
            type="button"
            class="role-btn"
            :class="{ active: role === 'teacher' }"
            @click="role = 'teacher'"
          >
            <strong>我是教师</strong>
            <span>创建班级、发布任务、查看学情</span>
          </button>
        </div>
      </template>

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
  width: 380px;
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

.role-picker {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.role-btn {
  flex: 1;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
  color: #475569;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.role-btn span {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.4;
}

.role-btn.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

.role-btn.active span {
  color: #60a5fa;
}

button[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-card > button:not(.role-btn) {
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

.login-card > button:not(.role-btn):hover:not(:disabled) {
  background: #2563eb;
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
