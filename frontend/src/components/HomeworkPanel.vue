<script setup>
import { computed, onActivated, ref, nextTick } from 'vue'
import {
  getSubmission,
  joinClass,
  listAssignments,
  listClasses,
  submitTextAnswer,
} from '../api.js'
import { state } from '../session.js'
import {
  assignmentStatus,
  statusLabels,
  sortAssignments,
} from '../assignments.js'
import AsyncState from './AsyncState.vue'
import { chapterLabel } from '../kp.js'
import { renderMarkdown } from '../markdown.js'

const emit = defineEmits(['start-assignment'])

const classes = ref([])
const currentClassId = ref(null)
const assignments = ref([])
const selectedId = ref(null)
const detail = ref(null)
const filter = ref('all')
const loading = ref(false)
const loadError = ref('')
const detailLoading = ref(false)
const detailError = ref('')
const drafts = new Map()
let classRequest = 0,
  detailRequest = 0,
  handledNavigation = 0
const message = ref('')
const error = ref('')

const joinCode = ref('')
const joining = ref(false)

const answer = ref('')
const submitting = ref(false)

const currentClass = computed(
  () => classes.value.find((item) => item.id === currentClassId.value) || null
)
const selected = computed(
  () => assignments.value.find((item) => item.id === selectedId.value) || null
)
const isClosed = computed(
  () =>
    !!selected.value && selected.value.is_overdue && !selected.value.allow_late
)

const filters = [
  { key: 'all', label: '全部' },
  { key: 'todo', label: '待提交' },
  { key: 'returned', label: '待重做' },
  { key: 'pending', label: '待批阅' },
  { key: 'graded', label: '已批阅' },
]
const filtered = computed(() =>
  sortAssignments(
    assignments.value.filter(
      (item) =>
        filter.value === 'all' || assignmentStatus(item) === filter.value
    )
  )
)

const diagnosis = computed(() => {
  if (!detail.value?.diagnosis) return null
  try {
    const parsed = JSON.parse(detail.value.diagnosis)
    if (!parsed || !Object.keys(parsed).length) return null
    if (!parsed.error_types?.length && !parsed.kp_ids?.length) return null
    return parsed
  } catch {
    return null
  }
})

function rememberDraft() {
  if (selectedId.value) drafts.set(selectedId.value, answer.value)
}
async function loadClasses() {
  loadError.value = ''
  loading.value = true
  try {
    const data = await listClasses()
    classes.value = data.joined || []
    const target = state.navigation
    const direct =
      target?.tab === 'homework' && target.nonce !== handledNavigation
    if (direct) handledNavigation = target.nonce
    const classId =
      direct && classes.value.some((c) => c.id === target.classId)
        ? target.classId
        : currentClassId.value || classes.value[0]?.id
    if (classId) {
      currentClassId.value = classId
      await loadAssignments()
      if (loadError.value) return
      const item =
        assignments.value.find(
          (a) => a.id === (direct ? target.assignmentId : selectedId.value)
        ) || assignments.value[0]
      if (direct && item) filter.value = 'all'
      if (item) await select(item)
      else {
        selectedId.value = null
        detail.value = null
      }
    }
    if (direct && target.assignmentId)
      nextTick(() =>
        document
          .querySelector('.detail')
          ?.scrollIntoView({ block: 'start', behavior: 'smooth' })
      )
  } catch (e) {
    loadError.value = e.message || '班级加载失败'
  } finally {
    loading.value = false
  }
}
async function loadAssignments() {
  if (!currentClassId.value) return
  const request = ++classRequest
  loading.value = true
  loadError.value = ''
  try {
    const items = await listAssignments(currentClassId.value)
    if (request === classRequest) assignments.value = items
  } catch (e) {
    if (request === classRequest) loadError.value = e.message || '任务加载失败'
  } finally {
    if (request === classRequest) loading.value = false
  }
}
async function switchClass(id) {
  rememberDraft()
  ++detailRequest
  currentClassId.value = id
  selectedId.value = null
  detail.value = null
  await loadAssignments()
  if (!loadError.value && assignments.value.length)
    await select(assignments.value[0])
}
async function select(assignment) {
  rememberDraft()
  const request = ++detailRequest
  selectedId.value = assignment.id
  detail.value = null
  detailError.value = ''
  answer.value = drafts.get(assignment.id) || ''
  if (!assignment.my_submission) {
    detailLoading.value = false
    return
  }
  detailLoading.value = true
  try {
    const result = await getSubmission(assignment.my_submission.id)
    if (request === detailRequest) detail.value = result
  } catch (e) {
    if (request === detailRequest)
      detailError.value = e.message || '提交内容加载失败'
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}

function redo() {
  emit('start-assignment', {
    ...selected.value,
    class_name: currentClass.value?.name || '',
  })
}

async function submitText() {
  const content = answer.value.trim()
  if (!content) {
    error.value = '请先写下你的答案'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await submitTextAnswer(selected.value.id, content)
    message.value = '已提交'
    drafts.delete(selectedId.value)
    answer.value = ''
    await loadAssignments()
    const fresh = assignments.value.find((item) => item.id === selectedId.value)
    if (fresh?.my_submission)
      detail.value = await getSubmission(fresh.my_submission.id)
  } catch (e) {
    error.value = e.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

async function doJoin() {
  error.value = ''
  const code = joinCode.value.trim()
  if (!code) {
    error.value = '请输入邀请码'
    return
  }
  joining.value = true
  try {
    const result = await joinClass(code)
    message.value =
      result.status === 'already' ? '你已经在这个班级里了' : '加入成功'
    joinCode.value = ''
    await loadClasses()
    if (result.class) await switchClass(result.class.id)
  } catch (e) {
    error.value = e.message || '加入失败'
  } finally {
    joining.value = false
  }
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

onActivated(loadClasses)
</script>

<template>
  <div class="homework">
    <div class="topbar">
      <div class="class-tabs">
        <button
          v-for="item in classes"
          :key="item.id"
          class="class-tab"
          :class="{ active: item.id === currentClassId }"
          @click="switchClass(item.id)"
        >
          {{ item.name }}
        </button>
        <span v-if="currentClass" class="class-teacher"
          >{{ currentClass.teacher_name }} 老师</span
        >
      </div>
      <div class="join-inline">
        <input
          aria-label="班级邀请码"
          maxlength="6"
          v-model="joinCode"
          placeholder="邀请码加入班级"
          @keydown.enter="doJoin"
        />
        <button :disabled="joining" @click="doJoin">
          {{ joining ? '…' : '加入' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="ok">{{ message }}</p>

    <AsyncState
      v-if="loading || loadError"
      :loading="loading"
      :error="loadError"
      @retry="loadClasses"
    />
    <div v-else-if="classes.length === 0" class="empty big">
      还没有加入班级。<br />
      向老师要一个 6 位邀请码，粘贴到右上角即可。
    </div>

    <div v-else class="layout">
      <aside class="list">
        <div class="filters">
          <button
            v-for="option in filters"
            :key="option.key"
            :class="{ active: filter === option.key }"
            @click="filter = option.key"
          >
            {{ option.label
            }}<span>{{
              assignments.filter(
                (a) =>
                  option.key === 'all' || assignmentStatus(a) === option.key
              ).length
            }}</span>
          </button>
        </div>

        <div v-if="loading" class="empty small">加载中…</div>
        <div v-else-if="!filtered.length" class="empty small">
          没有符合条件的任务
        </div>

        <div
          v-for="item in filtered"
          :key="item.id"
          class="item"
          role="button"
          tabindex="0"
          @keydown.enter="select(item)"
          @keydown.space.prevent="select(item)"
          :class="{ active: item.id === selectedId }"
          @click="select(item)"
        >
          <div class="item-title">{{ item.title }}</div>
          <div class="item-meta">
            <span class="type" :class="item.type">{{
              item.type === 'code' ? '代码' : '问答'
            }}</span>
            <span :class="assignmentStatus(item)">
              {{ statusLabels[assignmentStatus(item)] }}
            </span>
            <span v-if="item.is_overdue && !item.my_submission" class="overdue"
              >已截止</span
            >
            <span class="due">{{ formatTime(item.due_at) }}</span>
          </div>
        </div>
      </aside>

      <section class="detail">
        <div v-if="!selected" class="empty big">从左侧选择一条任务</div>

        <template v-else>
          <header class="detail-head">
            <div class="title-row">
              <h3>{{ selected.title }}</h3>
              <span class="type" :class="selected.type">
                {{ selected.type === 'code' ? '代码类' : '问答类' }}
              </span>
            </div>
            <div class="meta">
              <span>截止：{{ formatTime(selected.due_at) }}</span>
              <span v-if="selected.is_overdue" class="overdue">
                {{
                  selected.allow_late
                    ? '已截止（仍可提交）'
                    : '已截止，不可提交'
                }}
              </span>
              <span v-for="kp in selected.kp_ids" :key="kp" class="kp-chip">
                {{ selected.kp_titles?.[kp] || chapterLabel(kp) }}
              </span>
            </div>
            <p v-if="selected.description" class="desc">
              {{ selected.description }}
            </p>
          </header>

          <AsyncState
            v-if="detailLoading || detailError"
            :loading="detailLoading"
            :error="detailError"
            @retry="select(selected)"
          />
          <div v-else-if="detail" class="submission">
            <div class="sub-head">
              <strong>我的提交</strong>
              <span
                >{{ formatTime(detail.submitted_at) }} ·
                {{
                  statusLabels[assignmentStatus({ my_submission: detail })]
                }}</span
              >
            </div>

            <div
              v-if="detail.status === 'graded' || detail.status === 'returned'"
              class="grade-box"
              :class="detail.status"
            >
              <div class="grade-main">
                <span>{{
                  detail.status === 'returned' ? '已退回重做' : '老师评阅'
                }}</span>
                <strong>{{ detail.score ?? '-' }}</strong>
                <span>分</span>
              </div>
              <p v-if="detail.feedback" class="grade-comment">
                {{ detail.feedback }}
              </p>
              <p v-else class="grade-comment muted">老师没有留下评语</p>
            </div>
            <p v-else class="pending-grade">已提交，等待老师批阅</p>

            <div v-if="diagnosis" class="chips">
              <span
                v-for="item in diagnosis.error_types"
                :key="item"
                class="chip error"
                >{{ item }}</span
              >
              <span v-if="diagnosis.severity" class="chip"
                >严重度：{{ diagnosis.severity }}</span
              >
              <span v-if="diagnosis.hint_level_reached" class="chip">
                提示层级：{{ diagnosis.hint_level_reached }}/3
              </span>
              <span v-for="kp in diagnosis.kp_ids" :key="kp" class="chip kp">{{
                kp
              }}</span>
            </div>

            <div
              v-if="detail.ai_result"
              class="ai-box"
              v-html="renderMarkdown(detail.ai_result)"
            ></div>

            <details class="code-details">
              <summary>查看我提交的内容</summary>
              <pre>{{ detail.content }}</pre>
            </details>

            <div v-if="selected.type === 'code' && !isClosed" class="actions">
              <button class="primary" @click="redo">重新提交</button>
            </div>
            <p v-else-if="isClosed" class="closed-tip">
              任务已截止，不再接受提交。
            </p>

            <div v-else-if="!isClosed" class="actions answer-box">
              <textarea
                aria-label="你的作业答案"
                v-model="answer"
                placeholder="修改后可以重新提交…"
              ></textarea>
              <button
                class="primary"
                :disabled="submitting"
                @click="submitText"
              >
                {{ submitting ? '提交中…' : '重新提交' }}
              </button>
            </div>
          </div>

          <div v-else class="submission empty-block">
            <p v-if="isClosed">这个任务已经截止，不能再提交了。</p>
            <template v-else>
              <p>还没有提交这个任务。</p>
              <template v-if="selected.type === 'code'">
                <button class="primary" @click="redo">去完成</button>
              </template>
              <template v-else>
                <textarea
                  aria-label="你的作业答案"
                  v-model="answer"
                  placeholder="写下你的答案…"
                ></textarea>
                <button
                  class="primary"
                  :disabled="submitting"
                  @click="submitText"
                >
                  {{ submitting ? '提交中…' : '提交答案' }}
                </button>
              </template>
            </template>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.homework {
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
}
.filters {
  flex-wrap: wrap;
}
.filters button {
  flex: 0 0 auto !important;
  padding: 7px 8px !important;
}
.filters button span {
  font-size: 10px;
  margin-left: 4px;
  opacity: 0.8;
}
.list {
  width: 285px !important;
}
.item:focus-visible {
  outline-offset: -3px;
}
.detail {
  background: #fff;
}
.detail-head {
  padding-bottom: 5px;
}
.layout {
  align-items: flex-start;
}
.detail {
  min-height: 460px;
  scroll-margin-top: 20px;
}
.list .item {
  background: #fff;
}
.list .item.active {
  background: #f0f5ff;
}
.filters {
  padding-bottom: 8px;
}
.item-title {
  font-weight: 550;
}
.detail .title-row {
  flex-wrap: wrap;
}
@media (max-width: 760px) {
  .homework {
    padding: 16px;
  }
  .list {
    width: 100% !important;
    max-height: 320px;
    overflow-y: auto;
  }
  .layout {
    gap: 20px;
  }
  .detail {
    width: 100%;
    padding: 16px !important;
  }
  .join-inline {
    width: 100%;
  }
  .join-inline input {
    flex: 1;
    width: auto !important;
    min-width: 0;
  }
  .sub-head {
    flex-wrap: wrap;
    gap: 5px;
  }
  .filters button {
    font-size: 11px !important;
  }
  .class-tabs {
    max-width: 100%;
  }
}

.homework {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.class-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.class-tab {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: white;
  font-size: 13px;
  cursor: pointer;
  color: #475569;
}

.class-tab.active {
  border-color: var(--primary);
  background: #eff6ff;
  color: #1d4ed8;
}

.class-teacher {
  font-size: 12px;
  color: var(--muted);
}

.join-inline {
  display: flex;
  gap: 6px;
}

.join-inline input {
  width: 170px;
  padding: 7px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 12px;
}

.join-inline button {
  padding: 7px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
}

.layout {
  display: flex;
  gap: 14px;
  min-height: 60vh;
}

.list {
  width: 270px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filters {
  display: flex;
  gap: 6px;
}

.filters button {
  flex: 1;
  padding: 5px 0;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #64748b;
  font-size: 12px;
  cursor: pointer;
}

.filters button.active {
  border-color: var(--primary);
  color: #1d4ed8;
  background: #eff6ff;
}

.item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
}

.item:hover {
  border-color: #bfdbfe;
}

.item.active {
  border-color: var(--primary);
  background: #f8fbff;
}

.item-title {
  font-size: 13px;
  color: #1e293b;
  margin-bottom: 6px;
  line-height: 1.4;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
}

.item-meta .graded {
  color: #15803d;
}

.item-meta .returned,
.item-meta .todo {
  color: #b45309;
}

.item-meta .overdue {
  color: #b91c1c;
  background: #fef2f2;
  border-radius: 4px;
  padding: 0 5px;
}

.overdue {
  color: #b91c1c;
}

.due {
  margin-left: auto;
}

.detail {
  flex: 1;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 20px;
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-row h3 {
  margin: 0;
  font-size: 17px;
  color: #1e293b;
}

.type {
  font-size: 12px;
  padding: 1px 7px;
  border-radius: 4px;
}

.type.code {
  background: #eff6ff;
  color: var(--primary);
}

.type.question {
  background: #fef3c7;
  color: #b45309;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin-top: 8px;
}

.kp-chip {
  background: #f1f5f9;
  color: #475569;
  border-radius: 4px;
  padding: 1px 6px;
  font-family: monospace;
}

.desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
  margin: 12px 0 0;
}

.grade-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.grade-box.returned {
  background: #fef2f2;
  border-color: #fecaca;
}

.grade-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  color: #475569;
}

.grade-main strong {
  font-size: 22px;
  color: #15803d;
}

.grade-box.returned .grade-main strong {
  color: #b91c1c;
}

.grade-comment {
  margin: 8px 0 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.6;
}

.grade-comment.muted {
  color: var(--muted);
}

.pending-grade {
  font-size: 12px;
  color: var(--muted);
  margin: 0 0 12px;
}

.closed-tip {
  font-size: 12px;
  color: #b91c1c;
  background: #fef2f2;
  border-radius: 6px;
  padding: 8px 12px;
  margin: 10px 0 0;
}

.submission {
  margin-top: 18px;
  border-top: 1px solid #f1f5f9;
  padding-top: 14px;
}

.sub-head {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #334155;
  margin-bottom: 10px;
}

.sub-head span {
  font-size: 12px;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.chip {
  font-size: 12px;
  padding: 2px 9px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
}

.chip.error {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.chip.kp {
  background: #eff6ff;
  color: #1d4ed8;
  font-family: monospace;
}

.ai-box {
  font-size: 13px;
  line-height: 1.75;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 14px;
}

.ai-box :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

.code-details {
  margin-top: 10px;
  font-size: 12px;
  color: #475569;
}

.code-details summary {
  cursor: pointer;
  color: var(--primary);
}

.code-details pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin-top: 8px;
}

.actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.answer-box {
  flex-direction: column;
  align-items: stretch;
}

textarea {
  width: 100%;
  min-height: 90px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}

.primary {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  font-size: 13px;
  cursor: pointer;
  align-self: flex-start;
}

.primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.empty {
  color: var(--muted);
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.empty.big {
  padding: 60px 20px;
  background: #f8fafc;
  border-radius: 12px;
  line-height: 2;
}

.empty.small {
  padding: 12px;
  font-size: 12px;
}

.empty-block {
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.empty-block textarea {
  margin: 12px 0;
}

.empty-block .primary {
  align-self: center;
}

.error {
  color: #ef4444;
  font-size: 12px;
  margin: 0;
}

.ok {
  color: #15803d;
  font-size: 12px;
  margin: 0;
}

@media (max-width: 900px) {
  .layout {
    flex-direction: column;
  }

  .list {
    width: auto;
  }
}
</style>
