<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AssistantPanel from './components/AssistantPanel.vue'
import HomeworkPanel from './components/HomeworkPanel.vue'
import KnowledgeStatus from './components/KnowledgeStatus.vue'
import ProfilePanel from './components/ProfilePanel.vue'
import StatusBanner from './components/StatusBanner.vue'
import SettingsModal from './components/SettingsModal.vue'
import StudentHome from './components/StudentHome.vue'
import TeacherHome from './components/TeacherHome.vue'
import TeacherPanel from './components/TeacherPanel.vue'
import ToastHost from './components/ToastHost.vue'
import Login from './Login.vue'
import { apiMe, apiStatus, clearToken, getToken } from './api.js'
import { clearAssignment, loadLlmKey, setUser, startAssignment, state } from './session.js'

const activeTab = ref('home')
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
        { key: 'home', icon: '🏠', label: '首页' },
        { key: 'workspace', icon: '🧑‍🏫', label: '班级管理' },
        { key: 'assistant', icon: '🤖', label: '学习助手' },
        { key: 'knowledge', icon: '📖', label: '知识库' },
        { key: 'profile', icon: '👤', label: '我的' },
      ]
    : [
        { key: 'home', icon: '🏠', label: '首页' },
        { key: 'homework', icon: '📚', label: '作业中心' },
        { key: 'assistant', icon: '🤖', label: '学习助手' },
        { key: 'knowledge', icon: '📖', label: '知识库' },
        { key: 'profile', icon: '👤', label: '我的' },
      ]
)

const currentTitle = computed(
  () => tabs.value.find((item) => item.key === activeTab.value)?.label || ''
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

// 用 #/tab 记录当前页签，刷新/分享链接能回到同一页
function applyHash() {
  const key = (window.location.hash || '').replace(/^#\/?/, '')
  if (key && tabs.value.some((tab) => tab.key === key)) {
    activeTab.value = key
  }
}

watch(activeTab, (value) => {
  const target = `#/${value}`
  if (window.location.hash !== target) {
    window.history.replaceState(null, '', target)
  }
})

onMounted(() => {
  checkAuth().then(applyHash)
  window.addEventListener('auth-expired', () => {
    loggedIn.value = false
  })
  window.addEventListener('hashchange', applyHash)
})
</script>

<template>
  <div v-if="checking" class="loading-screen">加载中…</div>

  <Login v-else-if="!loggedIn" @success="onLoginSuccess" />

  <div v-else class="shell">
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-mark">智</span>
        <span class="logo-text">智育助教</span>
      </div>

      <nav class="nav">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="icon">{{ tab.icon }}</span>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <div class="side-foot">
        <button class="me" @click="activeTab = 'profile'">
          <span class="avatar">{{ avatarText }}</span>
          <span class="me-text">
            <strong>{{ displayName }}</strong>
            <small>{{ isTeacher ? '教师' : '学生' }}</small>
          </span>
        </button>
        <div class="foot-actions">
          <button @click="showSettings = true">模型设置</button>
          <button class="danger" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h2>{{ currentTitle }}</h2>
          <p class="sub">基于 RAG 与苏格拉底教学法的数据结构智能助教 · 只启发，不泄题</p>
        </div>
      </header>

      <StatusBanner :status="status" @open-settings="showSettings = true" />

      <section class="view">
        <template v-if="isTeacher">
          <TeacherHome v-if="activeTab === 'home'" @goto="activeTab = $event" />
          <TeacherPanel v-else-if="activeTab === 'workspace'" />
          <AssistantPanel v-else-if="activeTab === 'assistant'" />
          <KnowledgeStatus v-else-if="activeTab === 'knowledge'" />
          <ProfilePanel v-else />
        </template>
        <template v-else>
          <StudentHome
            v-if="activeTab === 'home'"
            @goto="activeTab = $event"
            @start-assignment="onStartAssignment"
          />
          <HomeworkPanel
            v-else-if="activeTab === 'homework'"
            @start-assignment="onStartAssignment"
          />
          <AssistantPanel v-else-if="activeTab === 'assistant'" />
          <KnowledgeStatus v-else-if="activeTab === 'knowledge'" />
          <ProfilePanel v-else />
        </template>
      </section>
    </main>

    <ToastHost />
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

.shell {
  display: flex;
  min-height: 100vh;
  background: #f1f5f9;
  font-family: sans-serif;
}

.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: white;
  border-right: 1px solid #e8eef6;
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  position: sticky;
  top: 0;
  height: 100vh;
  box-sizing: border-box;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px 20px;
}

.logo-mark {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.nav button {
  display: flex;
  align-items: center;
  gap: 10px;
  border: none;
  background: transparent;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  text-align: left;
}

.nav button:hover {
  background: #f8fafc;
}

.nav button.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.nav .icon {
  font-size: 16px;
}

.side-foot {
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.me {
  display: flex;
  align-items: center;
  gap: 10px;
  border: none;
  background: transparent;
  padding: 6px;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
}

.me:hover {
  background: #f8fafc;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  color: white;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.me-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.me-text strong {
  font-size: 13px;
  color: #1e293b;
}

.me-text small {
  font-size: 11px;
  color: #94a3b8;
}

.foot-actions {
  display: flex;
  gap: 6px;
}

.foot-actions button {
  flex: 1;
  border: 1px solid #e2e8f0;
  background: white;
  color: #64748b;
  border-radius: 6px;
  padding: 5px 0;
  font-size: 12px;
  cursor: pointer;
}

.foot-actions button:hover {
  border-color: #3b82f6;
  color: #2563eb;
}

.foot-actions button.danger:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.main {
  flex: 1;
  min-width: 0;
  padding: 22px 28px 40px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 14px;
}

.topbar h2 {
  margin: 0 0 4px;
  font-size: 20px;
  color: #1e293b;
}

.topbar .sub {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

.view {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

@media (max-width: 900px) {
  .shell {
    flex-direction: column;
  }

  .sidebar {
    width: auto;
    height: auto;
    position: static;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    padding: 12px;
    overflow-x: auto;
  }

  .logo {
    padding: 0;
  }

  .logo-text {
    display: none;
  }

  .nav {
    flex-direction: row;
  }

  .nav button {
    white-space: nowrap;
    padding: 8px 10px;
  }

  .side-foot {
    flex-direction: row;
    border-top: none;
    padding-top: 0;
  }

  .me-text,
  .foot-actions button:first-child {
    display: none;
  }

  .main {
    padding: 16px;
  }
}
</style>
