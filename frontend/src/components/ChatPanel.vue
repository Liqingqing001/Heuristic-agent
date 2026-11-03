<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import hljs from '../highlight.js'
import {
  streamChat,
  listConversations,
  getConversationMessages,
  createConversation,
  deleteConversation,
} from '../api.js'
import { chapterLabel } from '../kp.js'
import { renderMarkdown } from '../markdown.js'
import { navigateTo } from '../session.js'
import { toast } from '../toast.js'
import AppIcon from './AppIcon.vue'
import AsyncState from './AsyncState.vue'
const conversations = ref([]),
  currentId = ref(null),
  messages = ref([]),
  input = ref(''),
  loading = ref(false),
  chatBox = ref(null)
const historyLoading = ref(false),
  historyError = ref(''),
  requestError = ref(''),
  follow = ref(true),
  newContent = ref(false),
  lastQuestion = ref('')
let controller = null,
  historyRequest = 0
function highlightBlocks() {
  nextTick(() =>
    chatBox.value
      ?.querySelectorAll('pre code:not([data-highlighted])')
      .forEach((block) => {
        try {
          hljs.highlightElement(block)
        } catch {}
      })
  )
}
function scrollToBottom(force = false) {
  if (!force && !follow.value) {
    newContent.value = true
    return
  }
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
  newContent.value = false
}
function onScroll() {
  const el = chatBox.value
  if (!el) return
  follow.value = el.scrollHeight - el.scrollTop - el.clientHeight < 70
  if (follow.value) newContent.value = false
}
async function loadConversations() {
  historyLoading.value = true
  historyError.value = ''
  try {
    conversations.value = await listConversations()
  } catch (e) {
    historyError.value = e.message || '历史记录加载失败'
  } finally {
    historyLoading.value = false
  }
}
async function newConversation() {
  if (loading.value) return
  try {
    const conv = await createConversation()
    if (!conv) return
    currentId.value = conv.id
    messages.value = []
    requestError.value = ''
    lastQuestion.value = ''
    await loadConversations()
  } catch (e) {
    toast(e.message || '新建会话失败', 'error')
  }
}
async function switchConversation(id) {
  if (loading.value || id === currentId.value) return
  const request = ++historyRequest
  try {
    const data = await getConversationMessages(id)
    if (request !== historyRequest) return
    currentId.value = id
    messages.value = data
    requestError.value = ''
    lastQuestion.value = ''
    follow.value = true
    scrollToBottom(true)
    highlightBlocks()
  } catch (e) {
    toast(e.message || '会话加载失败', 'error')
  }
}
async function removeConversation(id) {
  if (loading.value || !confirm('确定删除这个会话吗？聊天记录会一起删除。'))
    return
  try {
    await deleteConversation(id)
    if (currentId.value === id) {
      currentId.value = null
      messages.value = []
    }
    await loadConversations()
    toast('会话已删除', 'success')
  } catch (e) {
    toast('删除失败：' + e.message, 'error')
  }
}
async function send(retry = false) {
  const q = retry === true ? lastQuestion.value : input.value.trim()
  if (!q || loading.value) return
  if (retry === true && messages.value.at(-2)?.content === q)
    messages.value.splice(-2)
  lastQuestion.value = q
  input.value = ''
  requestError.value = ''
  follow.value = true
  messages.value.push(
    { role: 'user', content: q },
    { role: 'assistant', content: '' }
  )
  const ai = messages.value[messages.value.length - 1]
  loading.value = true
  controller = new AbortController()
  scrollToBottom(true)
  try {
    const done = await streamChat(
      { question: q, conversation_id: currentId.value },
      (token) => {
        ai.content += token
        scrollToBottom()
      },
      (error) => {
        requestError.value = String(error)
      },
      controller.signal
    )
    if (done?.conversation_id) currentId.value = done.conversation_id
    if (done?.references?.length) ai.references = done.references
    if (!done?.done && !requestError.value)
      requestError.value = '连接已中断，回答可能不完整，可以重试。'
  } catch (e) {
    requestError.value =
      e.name === 'AbortError'
        ? '已停止生成，可重试或继续提问。'
        : '连接失败，请检查网络后重试。'
  } finally {
    loading.value = false
    controller = null
    await loadConversations()
    scrollToBottom()
    highlightBlocks()
  }
}
function handleEnter(event) {
  if (!event.isComposing && event.keyCode !== 229 && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}
onMounted(loadConversations)
onBeforeUnmount(() => controller?.abort())
</script>
<template>
  <div class="chat-layout">
    <aside class="conv-sidebar" aria-label="历史会话">
      <button class="new-btn" :disabled="loading" @click="newConversation">
        ＋ 新建会话</button
      ><AsyncState
        v-if="historyLoading || historyError"
        :loading="historyLoading"
        :error="historyError"
        @retry="loadConversations"
      />
      <div v-else class="conv-list">
        <div
          v-for="c in conversations"
          :key="c.id"
          class="conv-item"
          :class="{ active: c.id === currentId }"
        >
          <button
            class="conversation-select"
            :disabled="loading"
            :aria-current="c.id === currentId ? 'true' : undefined"
            @click="switchConversation(c.id)"
          >
            {{ c.title }}</button
          ><button
            class="conv-del"
            :disabled="loading"
            :aria-label="`删除会话：${c.title}`"
            @click="removeConversation(c.id)"
          >
            ×
          </button>
        </div>
        <div v-if="!conversations.length" class="empty-hint small">
          你的思考，将从这里开始
        </div>
      </div>
    </aside>
    <div class="chat-main">
      <div
        ref="chatBox"
        class="chat-box"
        aria-label="对话记录"
        @scroll="onScroll"
      >
        <div v-if="!messages.length" class="chat-welcome">
          <span class="welcome-icon"
            ><AppIcon name="assistant" :size="30"
          /></span>
          <h3>今天，想弄懂什么？</h3>
          <p>描述你的疑问，我会陪你一步步梳理思路。</p>
          <div class="question-suggestions">
            <button
              v-for="q in [
                '链表插入时，为什么指针顺序很重要？',
                '如何理解递归的终止条件？',
                'AVL 树什么时候需要旋转？',
              ]"
              :key="q"
              @click="input = q"
            >
              {{ q }} <AppIcon name="arrow" :size="15" />
            </button>
          </div>
        </div>
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="message"
          :class="m.role"
        >
          <template v-if="m.role === 'user'">{{ m.content }}</template
          ><template v-else
            ><div v-html="renderMarkdown(m.content)"></div>
            <span
              v-if="loading && i === messages.length - 1 && !m.content"
              class="thinking"
              role="status"
              >正在梳理思路<span>•••</span></span
            >
            <div v-if="m.references?.length" class="refs">
              <span class="refs-label">参考知识点</span
              ><button
                v-for="reference in m.references"
                :key="reference.chunk_id || reference.kp_id || reference.source"
                class="ref"
                @click="
                  () => {
                    navigateTo('knowledge', {
                      kpId: reference.kp_id,
                      query: reference.title,
                      source: reference.source,
                      category: reference.category,
                      section: reference.section,
                    })
                  }
                "
              >
                {{ reference.title || chapterLabel(reference.kp_id) }} ↗
              </button>
            </div></template
          >
        </div>
      </div>
      <button
        v-if="newContent"
        class="new-content"
        @click="
          () => {
            follow = true
            scrollToBottom(true)
          }
        "
      >
        有新内容 ↓
      </button>
      <div v-if="requestError" class="stream-error" role="alert">
        <span>{{ requestError }}</span
        ><button :disabled="loading" @click="send(true)">重新生成</button>
      </div>
      <div class="input-bar">
        <textarea
          v-model="input"
          rows="2"
          aria-label="你的问题"
          placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
          @keydown.enter="handleEnter"
        ></textarea
        ><button
          v-if="loading"
          class="stop-button"
          @click="controller?.abort()"
        >
          停止生成</button
        ><button v-else :disabled="!input.trim()" @click="send()">
          发送 <AppIcon name="arrow" :size="16" />
        </button>
      </div>
      <p class="chat-disclaimer">
        助教会引导你思考；模型回答请结合课程内容判断。
      </p>
    </div>
  </div>
</template>
<style scoped>
.chat-main {
  position: relative;
}
.conv-item {
  padding: 6px 8px;
}
.conversation-select {
  flex: 1;
  min-width: 0;
  border: 0;
  background: none;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 6px 0;
  color: inherit;
  font-size: 13px;
}
.chat-welcome {
  margin: auto;
  max-width: 430px;
  padding: 22px 8px;
  text-align: center;
}
.welcome-icon {
  width: 60px;
  height: 60px;
  background: #edf2ff;
  border-radius: 18px;
  color: var(--primary);
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
}
.chat-welcome h3 {
  font-size: 22px;
  margin: 0 0 10px;
}
.chat-welcome p {
  font-size: 13px;
  color: var(--muted);
}
.question-suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 28px;
}
.question-suggestions button {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--border);
  background: white;
  border-radius: 9px;
  padding: 12px 14px;
  text-align: left;
  font-size: 12px;
  color: #526582;
}
.question-suggestions button:hover {
  border-color: #aec4f5;
  background: #f8faff;
}
.input-bar button {
  display: flex;
  align-items: center;
  gap: 9px;
  white-space: nowrap;
  padding: 0 14px;
}
.input-bar textarea {
  font-size: 13px;
}
.chat-disclaimer {
  text-align: center;
  font-size: 11px;
  color: var(--muted);
  margin: 10px 0 0;
}
.thinking {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
}
.thinking span {
  animation: pulse 1.2s infinite;
}
.stream-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #fff6ed;
  border: 1px solid #f6ddc0;
  border-radius: 8px;
  font-size: 12px;
  color: #925822;
  padding: 10px 12px;
  margin-top: 10px;
}
.stream-error button {
  background: none;
  border: 0;
  color: var(--primary);
  white-space: nowrap;
}
.new-content {
  position: absolute;
  bottom: 110px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  color: var(--primary);
  border: 1px solid #c3d3f8;
  border-radius: 20px;
  box-shadow: 0 3px 12px #24345b12;
  padding: 7px 15px;
  font-size: 12px;
}
.ref {
  cursor: pointer;
}
.stop-button {
  background: #526079 !important;
}
@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}
@media (max-width: 760px) {
  .chat-disclaimer {
    font-size: 10px;
  }
  .input-bar textarea {
    font-size: 16px;
  }
  .chat-welcome h3 {
    font-size: 21px;
  }
  .chat-welcome {
    padding: 20px 4px;
  }
  .input-bar button {
    padding: 0 10px;
    font-size: 12px;
  }
}
</style>
