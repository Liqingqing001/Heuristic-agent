<script setup>
import { ref } from 'vue'
import ChatPanel from './components/ChatPanel.vue'
import CodeAnalyze from './components/CodeAnalyze.vue'
import KnowledgeStatus from './components/KnowledgeStatus.vue'

const activeTab = ref('chat')
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>智育助教 Agent</h1>
      <p>基于 RAG 与苏格拉底教学法的数据结构智能助教 · 只启发，不泄题</p>
    </header>

    <nav class="tabs">
      <button :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">苏格拉底对话</button>
      <button :class="{ active: activeTab === 'code' }" @click="activeTab = 'code'">代码剖析</button>
      <button :class="{ active: activeTab === 'kb' }" @click="activeTab = 'kb'">知识库状态</button>
    </nav>

    <main class="content">
      <ChatPanel v-if="activeTab === 'chat'" />
      <CodeAnalyze v-else-if="activeTab === 'code'" />
      <KnowledgeStatus v-else />
    </main>
  </div>
</template>
