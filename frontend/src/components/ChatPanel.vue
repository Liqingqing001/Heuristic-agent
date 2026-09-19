<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import {
  streamChat,
  listConversations,
  getConversationMessages,
  createConversation,
  deleteConversation,
} from '../api.js'

const conversations = ref([])
const currentId = ref(null)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const chatBox = ref(null)

const renderMarkdown = (text) => marked.parse(text)

function highlightBlocks() {
  if (!chatBox.value) return
  chatBox.value.querySelectorAll('pre code').forEach((block) => {
    try {
      hljs.highlightElement(block)
    } catch (e) {
      /* 忽略高亮失败 */
    }
  })
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

async function loadConversations() {
  conversations.value = await listConversations()
}

async function newConversation() {
  if (loading.value) return
  const conv = await createConversation()
  currentId.value = conv.id
  messages.value = []
  await loadConversations()
}

async function switchConversation(id) {
  if (loading.value || id === currentId.value) return
  currentId.value = id
  messages.value = await getConversationMessages(id)
  scrollToBottom()
  highlightBlocks()
}

async function removeConversation(id) {
  await deleteConversation(id)
  if (currentId.value === id) {
    currentId.value = null
    messages.value = []
  }
  await loadConversations()
}

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  messages.value.push({ role: 'assistant', content: '' })
  const aiIndex = messages.value.length - 1
  loading.value = true

  const doneInfo = await streamChat(
    { question: q, conversation_id: currentId.value },
    (token) => {
      // 必须通过响应式数组索引访问，否则直接改原始对象不会触发流式渲染
      messages.value[aiIndex].content += token
      scrollToBottom()
    },
    (err) => {
      messages.value[aiIndex].content += `\n\n⚠️ 出错：${err}`
    }
  )

  // 若此前无会话（后端自动新建），回填返回的 conversation_id
  if (doneInfo && doneInfo.conversation_id) {
    currentId.value = doneInfo.conversation_id
  }

  loading.value = false
  await loadConversations() // 刷新标题与排序
  scrollToBottom()
  highlightBlocks()
}

onMounted(async () => {
    // 只加载历史会话列表，但不自动选中任何一个
    await loadConversations()
    // 保持新会话状态：无当前会话、无消息
    currentId.value = null
    messages.value = []
})
</script>

<template>
  <div class="chat-layout">
    <aside class="conv-sidebar">
      <button class="new-btn" @click="newConversation">＋ 新建会话</button>
      <div class="conv-list">
        <div
          v-for="c in conversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === currentId }"
          @click="switchConversation(c.id)"
        >
          <span class="conv-title">{{ c.title }}</span>
          <button class="conv-del" title="删除会话" @click.stop="removeConversation(c.id)">×</button>
        </div>
        <div v-if="conversations.length === 0" class="empty-hint small">暂无会话</div>
      </div>
    </aside>

    <div class="chat-main">
      <div ref="chatBox" class="chat-box">
        <div v-if="messages.length === 0" class="empty-hint">
          你好！我是你的数据结构助教。<br />
          试着问我：「怎么反转单链表？」或「AVL 树什么时候需要旋转？」
        </div>
        <div v-for="(m, i) in messages" :key="i" class="message" :class="m.role">
          <template v-if="m.role === 'user'">{{ m.content }}</template>
          <div v-else v-html="renderMarkdown(m.content)"></div>
        </div>
      </div>

      <div class="input-bar">
        <textarea
          v-model="input"
          rows="2"
          placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
          @keydown.enter.exact.prevent="send"
        ></textarea>
        <button :disabled="loading || !input.trim()" @click="send">发送</button>
      </div>
    </div>
  </div>
</template>
