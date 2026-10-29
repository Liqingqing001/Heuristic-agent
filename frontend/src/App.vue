<script setup>
import { computed, onMounted, ref } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import CodeAnalyze from './components/CodeAnalyze.vue'
import KnowledgeStatus from './components/KnowledgeStatus.vue'
import StatusBanner from './components/StatusBanner.vue'
import SettingsModal from './components/SettingsModal.vue'
import StudentPanel from './components/StudentPanel.vue'
import TeacherPanel from './components/TeacherPanel.vue'
import Login from './Login.vue'
import { apiMe, apiStatus, clearToken, getToken } from './api.js'
import { clearAssignment, loadLlmKey, setUser, state } from './session.js'

const activeTab = ref('chat')
const loggedIn = ref(false)
const showSettings = ref(false)
const status = ref(null)
const checking = ref(true)

const isTeacher = computed(() => state.user?.role === 'teacher')
const displayName = computed(() => state.user?.display_name || state.user?.username || '')

const tabs = computed(() =>
  isTeacher.value
    ? [
        { key: 'teacher', label: '教师工作台' },
        { key: 'chat', label: '对话' },
        { key: 'code', label: '代码剖析' },
        { key: 'kb', label: '知识库' },
      ]
    : [
        { key: 'chat', label: '对话' },
        { key: 'code', label: '代码剖析' },
        { key: 'class', label: '我的班级' },
        { key: 'kb', label: '知识库' },
      ]
)

async function refreshStatus() {
  status.value = await apiStatus()
  state.status = status.value
}

async function checkAuth() {
  checking.value = true
  loadLlmKey()
  if (!getToken()) {
    loggedIn.value = false
    checking.value = false
    return
  }
  const user = await apiMe()
  if (user) {
    setUser(user)
    loggedIn.value = true
    await refreshStatus()
  } else {
    loggedIn.value = false
    clearToken()
  }
  checking.value = false
}

function onLoginSuccess() {
  window.location.reload()
}

function logout() {
  if (!confirm('确定要退出登录吗？')) return
  clearToken()
  clearAssignment()
  window.location.reload()
}

function startAssignment(assignment) {
  state.activeAssignment = assignment
  activeTab.value = 'code'
}

onMounted(() => {
  checkAuth()
  window.addEventListener('auth-expired', () => {
    loggedIn.value = false
  })
})
</script>

<template>
  <div v-if="checking" class="loading-screen">加载中…</div>

  <Login v-else-if="!loggedIn" @success="onLoginSuccess" />

  <div v-else class="app">
    <header class="header">
      <div class="brand">
        <h1>智育助教 Agent</h1>
        <p>基于 RAG 与苏格拉底教学法的数据结构智能助教 · 只启发，不泄题</p>
      </div>
      <div class="user-bar">
        <span class="role-badge" :class="isTeacher ? 'teacher' : 'student'">
          {{ isTeacher ? '教师' : '学生' }}
        </span>
        <span class="name">👤 {{ displayName }}</span>
        <button class="link-btn" @click="showSettings = true">模型设置</button>
        <button class="link-btn danger" @click="logout">退出</button>
      </div>
    </header>

    <StatusBanner :status="status" @open-settings="showSettings = true" />

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <main class="content">
      <template v-if="isTeacher">
        <TeacherPanel v-if="activeTab === 'teacher'" />
        <ChatPanel v-else-if="activeTab === 'chat'" />
        <CodeAnalyze v-else-if="activeTab === 'code'" />
        <KnowledgeStatus v-else />
      </template>
      <template v-else>
        <ChatPanel v-if="activeTab === 'chat'" />
        <CodeAnalyze v-else-if="activeTab === 'code'" />
        <StudentPanel v-else-if="activeTab === 'class'" @start-assignment="startAssignment" />
        <KnowledgeStatus v-else />
      </template>
    </main>

    <SettingsModal
      :open="showSettings"
      :server-key="!!status?.server_key"
      @close="showSettings = false; refreshStatus()"
    />
  </div>
</template>

<style scoped>
.loading-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 14px;
}

.app {
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px;
  font-family: sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 16px;
  position: relative;
}

.header h1 {
  color: #3b82f6;
  margin: 0 0 6px;
  font-size: 24px;
}

.header p {
  color: #64748b;
  font-size: 13px;
  margin: 0;
}

.user-bar {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #64748b;
}

.role-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.role-badge.teacher {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.role-badge.student {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.name {
  font-size: 12px;
}

.link-btn {
  padding: 4px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}

.link-btn:hover {
  border-color: #3b82f6;
  color: #2563eb;
}

.link-btn.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.tabs {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 18px;
}

.tabs button {
  padding: 9px 20px;
  border: none;
  border-radius: 8px;
  background: #e2e8f0;
  cursor: pointer;
  font-size: 14px;
}

.tabs button.active {
  background: #3b82f6;
  color: white;
}

.content {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

@media (max-width: 820px) {
  .user-bar {
    position: static;
    justify-content: center;
    margin-top: 10px;
  }

  .tabs {
    flex-wrap: wrap;
  }
}
</style>
