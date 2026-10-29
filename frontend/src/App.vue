<script setup>
import { computed, onMounted, ref } from 'vue'
import AssistantPanel from './components/AssistantPanel.vue'
import HomeworkPanel from './components/HomeworkPanel.vue'
import KnowledgeStatus from './components/KnowledgeStatus.vue'
import ProfilePanel from './components/ProfilePanel.vue'
import StatusBanner from './components/StatusBanner.vue'
import SettingsModal from './components/SettingsModal.vue'
import TeacherPanel from './components/TeacherPanel.vue'
import Login from './Login.vue'
import { apiMe, apiStatus, clearToken, getToken } from './api.js'
import { clearAssignment, loadLlmKey, setUser, startAssignment, state } from './session.js'

const activeTab = ref('assistant')
const loggedIn = ref(false)
const showSettings = ref(false)
const status = ref(null)
const checking = ref(true)

const isTeacher = computed(() => state.user?.role === 'teacher')
const displayName = computed(
  () => state.user?.display_name || state.user?.real_name || state.user?.username || ''
)
const avatarText = computed(() => displayName.value.trim().slice(0, 1).toUpperCase() || '?')

const tabs = computed(() =>
  isTeacher.value
    ? [
        { key: 'workspace', label: '教师工作台' },
        { key: 'assistant', label: '学习助手' },
        { key: 'knowledge', label: '知识库' },
        { key: 'profile', label: '我的' },
      ]
    : [
        { key: 'assistant', label: '学习助手' },
        { key: 'homework', label: '作业中心' },
        { key: 'knowledge', label: '知识库' },
        { key: 'profile', label: '我的' },
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

function onStartAssignment(assignment) {
  startAssignment(assignment)
  activeTab.value = 'assistant'
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
        <button class="avatar-btn" :title="'个人资料'" @click="activeTab = 'profile'">
          {{ avatarText }}
        </button>
        <div class="user-meta">
          <span class="name">{{ displayName }}</span>
          <span class="role-badge" :class="isTeacher ? 'teacher' : 'student'">
            {{ isTeacher ? '教师' : '学生' }}
          </span>
        </div>
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
        <TeacherPanel v-if="activeTab === 'workspace'" />
        <AssistantPanel v-else-if="activeTab === 'assistant'" />
        <KnowledgeStatus v-else-if="activeTab === 'knowledge'" />
        <ProfilePanel v-else />
      </template>
      <template v-else>
        <AssistantPanel v-if="activeTab === 'assistant'" />
        <HomeworkPanel v-else-if="activeTab === 'homework'" @start-assignment="onStartAssignment" />
        <KnowledgeStatus v-else-if="activeTab === 'knowledge'" />
        <ProfilePanel v-else />
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
  max-width: 1120px;
  margin: 0 auto;
  padding: 20px;
  font-family: sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.brand h1 {
  color: #3b82f6;
  margin: 0 0 6px;
  font-size: 24px;
}

.brand p {
  color: #64748b;
  font-size: 13px;
  margin: 0;
}

.user-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #64748b;
}

.avatar-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.name {
  font-size: 13px;
  color: #334155;
}

.role-badge {
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
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
  padding: 9px 22px;
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
  .header {
    flex-direction: column;
  }

  .tabs {
    flex-wrap: wrap;
  }
}
</style>
