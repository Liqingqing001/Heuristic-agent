<script setup>
import { ref, onMounted } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import CodeAnalyze from './components/CodeAnalyze.vue'
import KnowledgeStatus from './components/KnowledgeStatus.vue'
import Login from './Login.vue'
import { getToken, clearToken, apiMe } from './api.js'

const activeTab = ref('chat')
const loggedIn = ref(false)
const username = ref('')

async function checkAuth() {
  if (!getToken()) {
    loggedIn.value = false
    return
  }
  const user = await apiMe()
  if (user) {
    loggedIn.value = true
    username.value = user.username
  } else {
    loggedIn.value = false
    clearToken()
  }
}

function onLoginSuccess() {
  window.location.reload()
}

function logout() {
  if (!confirm('确定要退出登录吗？')) return
  clearToken()
  window.location.reload()
}

onMounted(() => {
  checkAuth()
  window.addEventListener('auth-expired', () => {
    loggedIn.value = false
  })
})
</script>

<template>
  <Login v-if="!loggedIn" @success="onLoginSuccess" />

  <div v-else class="app">
    <header class="header">
      <h1>智育助教 Agent</h1>
      <p>基于 RAG 与苏格拉底教学法的数据结构智能助教 · 只启发，不泄题</p>
      <div class="user-bar">
        <span>👤 {{ username }}</span>
        <button class="logout-btn" @click="logout">退出</button>
      </div>
    </header>

    <nav class="tabs">
      <button :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">对话</button>
      <button :class="{ active: activeTab === 'code' }" @click="activeTab = 'code'">代码剖析</button>
      <button :class="{ active: activeTab === 'kb' }" @click="activeTab = 'kb'">知识库</button>
    </nav>

    <main class="content">
      <ChatPanel v-if="activeTab === 'chat'" />
      <CodeAnalyze v-else-if="activeTab === 'code'" />
      <KnowledgeStatus v-else />
    </main>
  </div>
</template>

<style scoped>
.app { max-width: 900px; margin: 0 auto; padding: 20px; font-family: sans-serif; }
.header { text-align: center; margin-bottom: 20px; position: relative; }
.header h1 { color: #3b82f6; margin: 0 0 6px; }
.header p { color: #64748b; font-size: 13px; margin: 0; }
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
.logout-btn {
  padding: 4px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}
.logout-btn:hover { border-color: #ef4444; color: #ef4444; }
.tabs { display: flex; gap: 10px; justify-content: center; margin-bottom: 20px; }
.tabs button {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #e2e8f0;
  cursor: pointer;
  font-size: 15px;
}
.tabs button.active { background: #3b82f6; color: white; }
.content { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
</style>