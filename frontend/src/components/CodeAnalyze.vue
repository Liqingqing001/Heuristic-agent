<script setup>
import {
  computed,
  ref,
  nextTick,
  onMounted,
  onBeforeUnmount,
  defineAsyncComponent,
  watch,
} from 'vue'
import hljs from '../highlight.js'
import {
  streamAnalyze,
  listCodeAnalyses,
  getCodeAnalysis,
  deleteCodeAnalysis,
} from '../api.js'
import { clearAssignment, state } from '../session.js'
import { chapterLabel } from '../kp.js'
import { renderMarkdown } from '../markdown.js'
import { toast } from '../toast.js'
const CodeEditor = defineAsyncComponent(() => import('./CodeEditor.vue'))
const requestError = ref('')
const historyError = ref('')
let controller = null
onBeforeUnmount(() => controller?.abort())

// 表单状态
const code = ref('')
const language = ref('cpp')
const question = ref('')
const result = ref('')
const loading = ref(false)
const resultBox = ref(null)

// 来自「我的班级」的任务
const assignment = computed(() => state.activeAssignment)
const diagnosis = ref(null)
const submitted = ref(false)

function exitAssignment() {
  clearAssignment()
  diagnosis.value = null
  submitted.value = false
}

// 历史记录
const history = ref([])
const currentId = ref(null)

// 快捷指令
const activeAction = ref(null)
const quickActions = [
  {
    key: 'syntax',
    label: '语法检查',
    prompt:
      '请帮我检查这段代码的语法错误，不要直接改代码，用提问引导我自己发现。',
  },
  {
    key: 'diagnose',
    label: '代码诊断',
    prompt: '请帮我诊断这段代码的逻辑错误，不要直接给代码，用反问引导我思考。',
  },
  {
    key: 'optimize',
    label: '代码优化',
    prompt: '请帮我分析这段代码可以优化的地方，用提问引导我思考。',
  },
  {
    key: 'comment',
    label: '代码注释',
    prompt: '请引导我思考这段代码应该怎么加注释，而不是直接给我注释好的代码。',
  },
]

function toggleAction(action) {
  if (activeAction.value?.key === action.key) {
    activeAction.value = null
  } else {
    activeAction.value = action
  }
}

// ---- 加载历史列表 ----
async function loadHistory() {
  try {
    historyError.value = ''
    history.value = await listCodeAnalyses()
  } catch (e) {
    historyError.value = e.message || '历史记录加载失败'
  }
}

// ---- 会话操作 ----
function newSession() {
  if (loading.value) return
  diagnosis.value = null
  submitted.value = false
  currentId.value = null
  code.value = ''
  language.value = 'cpp'
  question.value = ''
  result.value = ''
  activeAction.value = null
}

async function switchSession(item) {
  if (loading.value) return
  try {
    const rec = await getCodeAnalysis(item.id)
    if (!rec) return
    currentId.value = rec.id
    code.value = rec.code
    language.value = rec.language
    question.value = rec.question || ''
    result.value = rec.result
    activeAction.value = null
    diagnosis.value = null
    submitted.value = false
    nextTick(() => highlight())
  } catch (e) {
    toast(e.message || '加载失败', 'error')
  }
}

async function removeSession(id) {
  if (!confirm('确定删除这条剖析记录吗？')) return
  try {
    await deleteCodeAnalysis(id)
    if (currentId.value === id) newSession()
    await loadHistory()
    toast('记录已删除', 'success')
  } catch (e) {
    toast('删除失败：' + (e.message || e), 'error')
  }
}

// ---- Markdown 与高亮 ----
function highlight() {
  if (!resultBox.value) return
  resultBox.value.querySelectorAll('pre code').forEach((b) => {
    try {
      hljs.highlightElement(b)
    } catch (e) {
      /* 忽略 */
    }
  })
}

// ---- 提交剖析 ----
async function submit() {
  const c = code.value.trim()
  if (!c || loading.value) return

  result.value = ''
  diagnosis.value = null
  submitted.value = false
  loading.value = true
  currentId.value = null // 提交后是新记录

  // 合并“模式指令”与“用户补充说明”
  let finalQuestion = ''
  if (activeAction.value) finalQuestion = activeAction.value.prompt
  if (question.value.trim()) {
    finalQuestion +=
      (finalQuestion ? '\n\n用户补充说明：' : '') + question.value.trim()
  }

  let accumulated = ''
  requestError.value = ''
  controller = new AbortController()
  try {
    const doneInfo = await streamAnalyze(
      {
        code: c,
        language: language.value,
        question: finalQuestion || null,
        assignment_id: assignment.value?.id ?? null,
      },
      (token) => {
        accumulated += token
        result.value = accumulated
      },
      (err) => {
        requestError.value = String(err)
      },
      controller.signal
    )

    // 用后端返回的 id 标记当前记录
    if (doneInfo && doneInfo.analysis_id) {
      currentId.value = doneInfo.analysis_id
    }
    if (doneInfo && doneInfo.diagnosis) {
      diagnosis.value = doneInfo.diagnosis
    }
    if (doneInfo && doneInfo.submission_id) {
      submitted.value = true
    }

    if (!doneInfo?.done && !requestError.value)
      requestError.value = '连接已中断，诊断可能不完整，请重试。'
  } catch (e) {
    requestError.value =
      e.name === 'AbortError'
        ? '已停止诊断，可以重新开始。'
        : '连接失败，请检查网络后重试。'
  } finally {
    loading.value = false
    controller = null
    await loadHistory()
    nextTick(() => highlight())
  }
}

watch(
  () => assignment.value?.id,
  () => {
    controller?.abort()
    diagnosis.value = null
    submitted.value = false
  }
)
onMounted(loadHistory)
</script>

<template>
  <div class="code-layout">
    <!-- 左侧历史记录 -->
    <aside class="conv-sidebar">
      <button class="new-btn" :disabled="loading" @click="newSession">
        ＋ 新建剖析
      </button>
      <div v-if="historyError" role="alert" class="stream-error">
        {{ historyError }} <button @click="loadHistory">重试</button>
      </div>
      <div class="conv-list">
        <div
          v-for="h in history"
          :key="h.id"
          class="conv-item"
          role="button"
          tabindex="0"
          @keydown.enter="switchSession(h)"
          @keydown.space.prevent="switchSession(h)"
          :class="{ active: h.id === currentId }"
          @click="switchSession(h)"
        >
          <span class="conv-title">{{ h.title }}</span>
          <button
            class="conv-del"
            :disabled="loading"
            title="删除"
            @click.stop="removeSession(h.id)"
          >
            ×
          </button>
        </div>
        <div v-if="history.length === 0" class="empty-hint small">暂无记录</div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <div class="code-main">
      <div v-if="assignment" class="assignment-banner">
        <div>
          <strong>正在完成任务：{{ assignment.title }}</strong>
          <span v-if="assignment.class_name" class="class-name"
            >· {{ assignment.class_name }}</span
          >
          <div class="tip">
            这次诊断会记录到任务提交里，老师可以在学情看板看到结果。
            <span v-if="submitted" class="done">已提交 ✓</span>
          </div>
        </div>
        <button class="exit-btn" @click="exitAssignment">退出任务</button>
      </div>

      <div class="code-form">
        <label class="editor-label"
          >你的代码 <span>切换页面时自动保留草稿</span></label
        ><CodeEditor v-model="code" />

        <div class="quick-actions">
          <button
            v-for="action in quickActions"
            :key="action.key"
            type="button"
            class="quick-btn"
            :class="{ active: activeAction?.key === action.key }"
            @click="toggleAction(action)"
          >
            {{ action.label }}
          </button>
        </div>

        <div class="row">
          <select v-model="language" aria-label="代码语言">
            <option value="cpp">C++</option>
            <option value="c">C</option>
          </select>
          <input
            aria-label="补充问题"
            v-model="question"
            placeholder="（可选）补充你的问题"
            style="flex: 1"
          />
          <button
            v-if="loading"
            class="stop-button"
            @click="controller?.abort()"
          >
            停止诊断
          </button>
          <button v-else :disabled="!code.trim()" @click="submit">
            {{ loading ? '诊断中…' : '开始剖析' }}
          </button>
        </div>
      </div>

      <div v-if="requestError" class="stream-error" role="alert">
        {{ requestError }}
        <button :disabled="loading" @click="submit">重试诊断</button>
      </div>
      <div v-if="loading && !result" class="thinking" role="status">
        正在分析代码，请稍候…
      </div>
      <div v-if="diagnosis" class="diag-chips">
        <span
          v-for="item in diagnosis.error_types"
          :key="item"
          class="chip error"
          >{{ item }}</span
        >
        <span class="chip">严重度：{{ diagnosis.severity }}</span>
        <span v-if="diagnosis.hint_level_reached" class="chip">
          提示层级：{{ diagnosis.hint_level_reached }}/3
        </span>
        <span v-for="kp in diagnosis.kp_ids" :key="kp" class="chip kp">
          {{ chapterLabel(kp) }}
        </span>
        <span v-if="submitted" class="chip done">已提交给老师</span>
      </div>

      <div
        v-if="result"
        ref="resultBox"
        class="result-box"
        v-html="renderMarkdown(result)"
      ></div>
      <div v-else class="empty-hint">
        提交一段代码，助教会先诊断逻辑问题，再用提问引导你自己修复——绝不直接给完整代码。
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-label {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.editor-label span {
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
}
.stream-error {
  padding: 12px;
  background: #fff6ed;
  color: #925822;
  border-radius: 8px;
  font-size: 12px;
}
.stream-error button {
  border: 0;
  background: none;
  color: var(--primary);
}
.thinking {
  padding: 12px;
  color: var(--muted);
  font-size: 13px;
}
.stop-button {
  background: #526079 !important;
}
.code-main {
  min-width: 0;
}
@media (max-width: 760px) {
  .code-layout {
    flex-direction: column;
    height: auto !important;
  }
  .code-main {
    overflow: visible !important;
  }
  .conv-sidebar {
    width: 100% !important;
    max-height: 150px;
  }
  .row {
    flex-wrap: wrap;
  }
  .row input {
    min-width: 0;
    flex-basis: 50% !important;
  }
  .assignment-banner {
    flex-wrap: wrap;
  }
  .editor-label span {
    display: none;
  }
}
.code-layout {
  display: flex;
  gap: 16px;
  height: 70vh;
}

.conv-sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.new-btn {
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.new-btn:hover {
  background: var(--primary);
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.conv-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #334155;
}

.conv-item:hover {
  background: #f1f5f9;
}

.conv-item.active {
  background: #dbeafe;
  color: #1d4ed8;
}

.conv-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-del {
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
}

.conv-del:hover {
  color: #ef4444;
}

.code-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.code-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

textarea {
  width: 100%;
  min-height: 180px;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-family: monospace;
  font-size: 13px;
  resize: vertical;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-btn {
  padding: 6px 14px;
  font-size: 13px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: #eff6ff;
}

.quick-btn.active {
  border-color: var(--primary);
  background: var(--primary);
  color: white;
}

.row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.row select,
.row input {
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
}

.row button {
  padding: 8px 18px;
  border: none;
  border-radius: 6px;
  background: var(--primary);
  color: white;
  font-size: 13px;
  cursor: pointer;
}

.row button:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.result-box {
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  line-height: 1.7;
  font-size: 14px;
  overflow-x: auto;
}

.result-box :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}

.empty-hint {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  padding: 20px;
}

.assignment-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 10px 14px;
}

.assignment-banner strong {
  color: #1d4ed8;
  font-size: 13px;
}

.assignment-banner .class-name {
  color: #60a5fa;
  font-size: 12px;
  margin-left: 4px;
}

.assignment-banner .tip {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.assignment-banner .done {
  color: #15803d;
  margin-left: 6px;
}

.exit-btn {
  border: 1px solid #93c5fd;
  background: white;
  color: #1d4ed8;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.diag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.diag-chips .chip {
  font-size: 12px;
  padding: 2px 9px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
}

.diag-chips .chip.error {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.diag-chips .chip.kp {
  background: #eff6ff;
  color: #1d4ed8;
  font-family: monospace;
}

.diag-chips .chip.done {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.empty-hint.small {
  font-size: 12px;
  padding: 10px;
}
</style>
