<script setup>
import {
  computed,
  defineAsyncComponent,
  h,
  nextTick,
  onMounted,
  ref,
  watch,
} from 'vue'
import AppIcon from './components/AppIcon.vue'
import AsyncState from './components/AsyncState.vue'
import StatusBanner from './components/StatusBanner.vue'
import SettingsModal from './components/SettingsModal.vue'
import ToastHost from './components/ToastHost.vue'
import Login from './Login.vue'
import { apiMe, apiStatus, clearToken, getToken } from './api.js'
import {
  clearAssignment,
  loadLlmKey,
  setUser,
  startAssignment,
  state,
  navigateTo,
} from './session.js'

const lazy = (loader) =>
  defineAsyncComponent({
    loader,
    loadingComponent: { render: () => h(AsyncState, { loading: true }) },
    errorComponent: {
      render: () =>
        h(AsyncState, {
          error: '页面加载失败，请检查网络后重试。',
          onRetry: () => window.location.reload(),
        }),
    },
    delay: 150,
    timeout: 20000,
  })
const pages = {
  studentHome: lazy(() => import('./components/StudentHome.vue')),
  teacherHome: lazy(() => import('./components/TeacherHome.vue')),
  homework: lazy(() => import('./components/HomeworkPanel.vue')),
  workspace: lazy(() => import('./components/TeacherPanel.vue')),
  assistant: lazy(() => import('./components/AssistantPanel.vue')),
  knowledge: lazy(() => import('./components/KnowledgeStatus.vue')),
  profile: lazy(() => import('./components/ProfilePanel.vue')),
}
const activeTab = ref('home')
const loggedIn = ref(false)
const showSettings = ref(false)
const status = ref(null)
const checking = ref(true)
const authError = ref('')
const isTeacher = computed(() => state.user?.role === 'teacher')
const displayName = computed(
  () =>
    state.user?.display_name ||
    state.user?.real_name ||
    state.user?.username ||
    ''
)
const avatarText = computed(
  () => displayName.value.trim().slice(0, 1).toUpperCase() || '?'
)
const tabs = computed(() => [
  {
    key: 'home',
    icon: 'home',
    label: '首页',
    description: isTeacher.value ? '教学概览' : '学习概览',
  },
  isTeacher.value
    ? {
        key: 'workspace',
        icon: 'workspace',
        label: '班级管理',
        description: '任务与学情',
      }
    : {
        key: 'homework',
        icon: 'homework',
        label: '作业中心',
        description: '任务与反馈',
      },
  {
    key: 'assistant',
    icon: 'assistant',
    label: '学习助手',
    description: '提问与代码诊断',
  },
  {
    key: 'knowledge',
    icon: 'book',
    label: '知识库',
    description: '理解每个知识点',
  },
  {
    key: 'profile',
    icon: 'profile',
    label: '我的',
    description: '账户与个人资料',
  },
])
const current = computed(
  () => tabs.value.find((t) => t.key === activeTab.value) || tabs.value[0]
)
const pageKey = computed(() =>
  activeTab.value === 'home'
    ? isTeacher.value
      ? 'teacherHome'
      : 'studentHome'
    : activeTab.value
)
const dateLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())
async function refreshStatus() {
  try {
    status.value = await apiStatus()
    state.status = status.value
  } catch {
    status.value = { unavailable: true }
    state.status = status.value
  }
}
async function checkAuth() {
  checking.value = true
  authError.value = ''
  loadLlmKey()
  try {
    if (!getToken()) {
      loggedIn.value = false
      return
    }
    const user = await apiMe()
    if (user) {
      setUser(user)
      loggedIn.value = true
      refreshStatus()
    } else {
      loggedIn.value = false
      clearToken()
    }
  } catch (e) {
    authError.value = e.message || '无法连接服务，请稍后重试'
  } finally {
    checking.value = false
  }
}
function clearSession() {
  clearToken()
  clearAssignment()
  setUser(null)
  state.navigation = null
  activeTab.value = 'home'
  status.value = null
  showSettings.value = false
  loggedIn.value = false
}
function logout() {
  if (confirm('确定要退出登录吗？')) clearSession()
}

function onStartAssignment(assignment) {
  startAssignment(assignment)
  navigateTo('assistant')
}
function applyHash() {
  const key = window.location.hash.replace(/^#\/?/, '')
  if (tabs.value.some((t) => t.key === key)) activeTab.value = key
}
watch(
  () => state.navigation,
  (target) => {
    if (target && tabs.value.some((t) => t.key === target.tab))
      activeTab.value = target.tab
  }
)
watch(activeTab, (value) => {
  nextTick(() => window.scrollTo({ top: 0 }))
  if (window.location.hash !== `#/${value}`)
    window.history.pushState(null, '', `#/${value}`)
})
onMounted(() => {
  checkAuth().then(applyHash)
  window.addEventListener('auth-expired', clearSession)
  window.addEventListener('hashchange', applyHash)
})
</script>

<template>
  <div v-if="checking" class="boot-screen">
    <span class="brand-mark">智</span>
    <p>正在准备你的学习空间…</p>
  </div>
  <div v-else-if="authError" class="boot-screen">
    <AsyncState :error="authError" @retry="checkAuth" /><button
      class="ui-button"
      @click="
        () => {
          clearToken()
          authError = ''
          loggedIn = false
        }
      "
    >
      返回登录
    </button>
  </div>
  <Login v-else-if="!loggedIn" @success="checkAuth().then(applyHash)" />
  <div v-else class="shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">智</span>
        <div><strong>智育助教</strong><small>让思考发生</small></div>
      </div>
      <div class="nav-caption">
        {{ isTeacher ? '教学工作台' : '我的学习空间' }}
      </div>
      <nav class="nav" aria-label="主要导航">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="{ active: activeTab === tab.key }"
          :aria-current="activeTab === tab.key ? 'page' : undefined"
          @click="activeTab = tab.key"
        >
          <AppIcon :name="tab.icon" /><span>{{ tab.label }}</span
          ><span v-if="activeTab === tab.key" class="nav-dot"></span>
        </button>
      </nav>
      <div class="side-note">
        <AppIcon name="light" :size="22" /><strong>每一次提问，都是进步</strong>
        <p>从一个小问题开始，慢慢找到自己的答案。</p>
      </div>
      <div class="side-foot">
        <button class="me" @click="activeTab = 'profile'">
          <span class="avatar">{{ avatarText }}</span
          ><span
            ><strong>{{ displayName }}</strong
            ><small>{{ isTeacher ? '教师账户' : '学生账户' }}</small></span
          ></button
        ><button class="logout" @click="logout">退出登录</button>
      </div>
    </aside>
    <main id="main-content" class="main" tabindex="-1">
      <header class="topbar">
        <div>
          <span class="eyebrow">{{
            isTeacher ? 'TEACHING WORKSPACE' : 'LEARNING WORKSPACE'
          }}</span>
          <h1>
            {{ current.label }}<span>{{ current.description }}</span>
          </h1>
        </div>
        <div class="top-actions">
          <span class="date-label">{{ dateLabel }}</span
          ><button class="settings-button" @click="showSettings = true">
            <AppIcon name="settings" :size="18" /><span>模型设置</span>
          </button>
        </div>
      </header>
      <StatusBanner
        :status="status"
        @open-settings="showSettings = true"
        @retry="refreshStatus"
      />
      <section class="view" :aria-label="current.label">
        <KeepAlive
          ><component
            :is="pages[pageKey]"
            :key="pageKey"
            @goto="activeTab = $event"
            @start-assignment="onStartAssignment"
            @open-settings="showSettings = true"
        /></KeepAlive>
      </section>
      <footer class="page-footer">智育助教 · 引导思考，陪伴成长</footer>
    </main>
    <nav class="mobile-nav" aria-label="移动端导航">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        :aria-current="activeTab === tab.key ? 'page' : undefined"
        @click="activeTab = tab.key"
      >
        <AppIcon :name="tab.icon" /><span>{{ tab.label }}</span>
      </button>
    </nav>
    <ToastHost />
    <SettingsModal
      :open="showSettings"
      :server-key="!!status?.server_key"
      @close="
        () => {
          showSettings = false
          refreshStatus()
        }
      "
    />
  </div>
</template>
<style scoped>
.boot-screen {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  gap: 12px;
}
.shell {
  display: flex;
  min-height: 100dvh;
}
.sidebar {
  width: 236px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 30px 18px 20px;
  position: sticky;
  top: 0;
  height: 100dvh;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px 38px;
}
.brand strong {
  display: block;
  font-size: 19px;
  letter-spacing: 1px;
}
.brand small {
  display: block;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 3px;
  margin-top: 4px;
}
.nav-caption {
  font-size: 11px;
  letter-spacing: 2px;
  color: #52627a;
  padding: 0 14px 14px;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.nav button {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 13px 15px;
  border: 0;
  border-radius: 10px;
  background: none;
  color: #526079;
  font-size: 14px;
  text-align: left;
}
.nav button:hover {
  background: var(--surface);
}
.nav button.active {
  background: #edf3ff;
  color: var(--primary);
  font-weight: 650;
}
.nav-dot {
  width: 6px;
  height: 6px;
  background: var(--primary);
  border-radius: 50%;
  margin-left: auto;
}
.side-note {
  margin-top: auto;
  padding: 22px 14px 24px;
  color: var(--primary);
}
.side-note strong {
  display: block;
  font-size: 12px;
  margin-top: 10px;
}
.side-note p {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.8;
}
.side-foot {
  border-top: 1px solid var(--border);
  padding: 18px 8px 0;
}
.me {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  background: none;
  text-align: left;
  padding: 0;
  max-width: 100%;
}
.me strong {
  display: block;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.me small {
  display: block;
  color: var(--muted);
  font-size: 11px;
  margin-top: 3px;
}
.avatar {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  background: #e9efff;
  color: var(--primary);
  border-radius: 12px;
  font-weight: 700;
}
.logout {
  padding: 12px 0 0;
  border: 0;
  background: none;
  font-size: 12px;
  color: var(--muted);
}
.main {
  flex: 1;
  min-width: 0;
  padding: 30px 36px 14px;
  max-width: 1700px;
  margin: 0 auto;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.eyebrow {
  font-size: 10px;
  letter-spacing: 2.2px;
  color: var(--muted);
}
.topbar h1 {
  font-size: 25px;
  margin: 7px 0 0;
  font-weight: 700;
  letter-spacing: -0.6px;
}
.topbar h1 span {
  font-size: 13px;
  font-weight: 400;
  color: var(--muted);
  letter-spacing: 0;
  border-left: 1px solid #ccd5e3;
  margin-left: 16px;
  padding-left: 16px;
}
.top-actions {
  display: flex;
  gap: 20px;
  align-items: center;
}
.date-label {
  font-size: 12px;
  color: var(--muted);
}
.settings-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  border: 1px solid var(--border);
  padding: 9px 13px;
  border-radius: 9px;
  color: #475569;
  font-size: 12px;
}
.view {
  min-height: 65vh;
}
.page-footer {
  text-align: center;
  color: #52627a;
  font-size: 11px;
  padding: 24px 0 10px;
  letter-spacing: 1px;
}
.mobile-nav {
  display: none;
}
.skip-link {
  position: fixed;
  top: -80px;
  left: 10px;
  z-index: 100;
  background: white;
  padding: 12px;
}
.skip-link:focus {
  top: 10px;
}
@media (max-width: 1100px) {
  .sidebar {
    width: 204px;
  }
  .main {
    padding: 25px 24px;
  }
  .date-label {
    display: none;
  }
  .topbar h1 span {
    display: none;
  }
}
@media (max-width: 760px) {
  .sidebar {
    display: none;
  }
  .main {
    padding: 22px 16px calc(88px + env(safe-area-inset-bottom));
  }
  .topbar {
    margin-bottom: 18px;
  }
  .topbar h1 {
    font-size: 24px;
  }
  .top-actions {
    gap: 6px;
  }
  .settings-button {
    padding: 9px;
  }
  .mobile-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.97);
    border-top: 1px solid var(--border);
    z-index: 30;
    padding: 8px 8px calc(8px + env(safe-area-inset-bottom));
    box-shadow: 0 -4px 24px #24345b08;
  }
  .mobile-nav button {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    background: none;
    border: 0;
    color: #64748b;
    font-size: 11px;
    padding: 6px 0;
    border-radius: 10px;
  }
  .mobile-nav button.active {
    background: #eef3ff;
    color: var(--primary);
    font-weight: 650;
  }
  .eyebrow {
    font-size: 9px;
  }
  .page-footer {
    font-size: 10px;
  }
}
</style>
