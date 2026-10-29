<script setup>
import { computed, onMounted, ref } from 'vue'
import { marked } from 'marked'
import {
  createAssignment,
  createClass,
  getOverview,
  getSubmission,
  listAssignments,
  listClasses,
  listSubmissions,
} from '../api.js'

const classes = ref([])
const currentId = ref(null)
const assignments = ref([])
const overview = ref(null)
const loading = ref(false)
const message = ref('')
const error = ref('')

const showCreateClass = ref(false)
const newClassName = ref('')
const newClassTerm = ref('')

const newAssignment = ref({
  title: '',
  description: '',
  type: 'code',
  kp_ids: '',
  due_at: '',
})

const submissions = ref([])
const submissionsTitle = ref('')
const detail = ref(null)

const currentClass = computed(
  () => classes.value.find((item) => item.id === currentId.value) || null
)

const averageRate = computed(() => {
  if (!overview.value?.assignments?.length) return 0
  const list = overview.value.assignments
  return Math.round((list.reduce((sum, item) => sum + item.rate, 0) / list.length) * 100)
})

async function loadClasses() {
  const data = await listClasses()
  classes.value = data.taught || []
  if (!currentId.value && classes.value.length) {
    await selectClass(classes.value[0].id)
  }
}

async function selectClass(id) {
  currentId.value = id
  overview.value = null
  submissions.value = []
  loading.value = true
  const [items, stats] = await Promise.all([listAssignments(id), getOverview(id)])
  assignments.value = items
  overview.value = stats
  loading.value = false
}

async function doCreateClass() {
  error.value = ''
  const name = newClassName.value.trim()
  if (!name) {
    error.value = '班级名称不能为空'
    return
  }
  try {
    const cls = await createClass(name, newClassTerm.value.trim())
    newClassName.value = ''
    newClassTerm.value = ''
    showCreateClass.value = false
    await loadClasses()
    await selectClass(cls.id)
    message.value = `班级已创建，邀请码：${cls.code}`
  } catch (e) {
    error.value = e.message || '创建失败'
  }
}

async function doCreateAssignment() {
  error.value = ''
  const payload = {
    title: newAssignment.value.title.trim(),
    description: newAssignment.value.description.trim(),
    type: newAssignment.value.type,
    kp_ids: newAssignment.value.kp_ids
      .split(/[,，\s]+/)
      .map((item) => item.trim())
      .filter(Boolean),
    due_at: newAssignment.value.due_at || null,
  }
  if (!payload.title) {
    error.value = '任务标题不能为空'
    return
  }
  try {
    await createAssignment(currentId.value, payload)
    newAssignment.value = { title: '', description: '', type: 'code', kp_ids: '', due_at: '' }
    await selectClass(currentId.value)
    message.value = '任务已发布'
  } catch (e) {
    error.value = e.message || '发布失败'
  }
}

async function openSubmissions(assignment) {
  submissionsTitle.value = assignment.title
  submissions.value = await listSubmissions(assignment.id)
}

async function openDetail(item) {
  detail.value = await getSubmission(item.id)
}

function closeDetail() {
  detail.value = null
}

async function copyCode() {
  if (!currentClass.value) return
  try {
    await navigator.clipboard.writeText(currentClass.value.code)
    message.value = '邀请码已复制'
  } catch {
    message.value = `邀请码：${currentClass.value.code}`
  }
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

const renderMarkdown = (text) => marked.parse(text || '')

onMounted(loadClasses)
</script>

<template>
  <div class="teacher-panel">
    <div class="toolbar">
      <div class="class-tabs">
        <button
          v-for="item in classes"
          :key="item.id"
          class="class-tab"
          :class="{ active: item.id === currentId }"
          @click="selectClass(item.id)"
        >
          {{ item.name }}
          <span class="count">{{ item.member_count }} 人</span>
        </button>
        <button class="class-tab add" @click="showCreateClass = !showCreateClass">＋ 新建班级</button>
      </div>
    </div>

    <div v-if="showCreateClass" class="card form-card">
      <div class="row">
        <input v-model="newClassName" placeholder="班级名称，例如：数据结构 2026 春" />
        <input v-model="newClassTerm" placeholder="学期（可选）" class="short" />
        <button class="primary" @click="doCreateClass">创建</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="ok">{{ message }}</p>

    <div v-if="!classes.length" class="empty">
      还没有班级。先点「＋ 新建班级」，把生成的 6 位邀请码发给学生。
    </div>

    <template v-else-if="currentClass">
      <div class="class-head">
        <div>
          <h3>{{ currentClass.name }}</h3>
          <span class="sub">{{ currentClass.term || '未填写学期' }} · {{ currentClass.member_count }} 名学生</span>
        </div>
        <button class="invite" @click="copyCode">
          邀请码 <strong>{{ currentClass.code }}</strong>（点击复制）
        </button>
      </div>

      <!-- 学情看板 -->
      <div v-if="overview" class="stat-grid">
        <div class="stat">
          <b>{{ overview.member_count }}</b>
          <span>学生人数</span>
        </div>
        <div class="stat">
          <b>{{ overview.assignment_count }}</b>
          <span>任务数</span>
        </div>
        <div class="stat">
          <b>{{ averageRate }}%</b>
          <span>平均提交率</span>
        </div>
      </div>

      <div v-if="overview" class="two-col">
        <div class="card">
          <h4>任务提交情况</h4>
          <div v-if="!overview.assignments.length" class="empty small">还没有任务</div>
          <div v-for="item in overview.assignments" :key="item.id" class="progress-row">
            <div class="progress-label">
              <span>{{ item.title }}</span>
              <span class="num">{{ item.submitted }}/{{ item.member_count }}</span>
            </div>
            <div class="bar"><div class="fill" :style="{ width: `${Math.round(item.rate * 100)}%` }"></div></div>
          </div>
        </div>

        <div class="card">
          <h4>错因分布</h4>
          <div v-if="!overview.error_distribution.length" class="empty small">
            暂无诊断数据（学生提交后自动统计）
          </div>
          <div
            v-for="item in overview.error_distribution"
            :key="item.type"
            class="progress-row"
          >
            <div class="progress-label">
              <span>{{ item.type }}</span>
              <span class="num">{{ item.count }}</span>
            </div>
            <div class="bar error-bar">
              <div
                class="fill error"
                :style="{ width: `${Math.round((item.count / overview.error_distribution[0].count) * 100)}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="overview" class="card">
        <h4>学生进度</h4>
        <div v-if="!overview.students.length" class="empty small">还没有学生加入</div>
        <table v-else class="table">
          <thead>
            <tr><th>学生</th><th>提交</th><th>进度</th><th>未交任务</th></tr>
          </thead>
          <tbody>
            <tr v-for="student in overview.students" :key="student.user_id">
              <td>{{ student.display_name || student.username }}</td>
              <td>{{ student.submitted }}/{{ student.total }}</td>
              <td>
                <div class="bar small-bar">
                  <div class="fill" :style="{ width: `${Math.round(student.rate * 100)}%` }"></div>
                </div>
              </td>
              <td class="missing">{{ student.missing.join('、') || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 发布任务 -->
      <div class="card">
        <h4>发布任务</h4>
        <div class="form-grid">
          <input v-model="newAssignment.title" placeholder="任务标题，例如：单链表插入训练" />
          <select v-model="newAssignment.type">
            <option value="code">代码类（AI 诊断）</option>
            <option value="question">问答类（文字提交）</option>
          </select>
          <input v-model="newAssignment.kp_ids" placeholder="关联知识点，逗号分隔，例如 ds-01-02, ds-01-03" />
          <input v-model="newAssignment.due_at" type="datetime-local" />
          <textarea v-model="newAssignment.description" placeholder="任务说明（可选）"></textarea>
          <button class="primary" @click="doCreateAssignment">发布</button>
        </div>
      </div>

      <div class="card">
        <h4>任务列表</h4>
        <div v-if="loading" class="empty small">加载中…</div>
        <div v-else-if="!assignments.length" class="empty small">还没有任务</div>
        <div v-for="item in assignments" :key="item.id" class="assignment-row">
          <div>
            <strong>{{ item.title }}</strong>
            <span class="type">{{ item.type === 'code' ? '代码' : '问答' }}</span>
            <span class="sub">截止 {{ formatTime(item.due_at) }}</span>
            <span v-for="kp in item.kp_ids" :key="kp" class="kp-chip">{{ kp }}</span>
          </div>
          <button class="ghost" @click="openSubmissions(item)">
            查看提交（{{ item.submitted_count }}）
          </button>
        </div>
      </div>

      <div v-if="submissions.length" class="card">
        <h4>「{{ submissionsTitle }}」的提交</h4>
        <table class="table">
          <thead><tr><th>学生</th><th>时间</th><th>状态</th><th>诊断</th><th></th></tr></thead>
          <tbody>
            <tr v-for="item in submissions" :key="item.id">
              <td>{{ item.display_name || item.username }}</td>
              <td>{{ formatTime(item.submitted_at) }}</td>
              <td>{{ item.status }}</td>
              <td class="diagnosis-cell">{{ item.diagnosis }}</td>
              <td><button class="link" @click="openDetail(item)">查看</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-if="detail" class="mask" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-head">
          <h3>{{ detail.display_name || detail.username }} 的提交</h3>
          <button class="link" @click="closeDetail">关闭</button>
        </div>
        <p class="sub">{{ formatTime(detail.submitted_at) }} · {{ detail.language }}</p>
        <div class="diag-box" v-if="detail.diagnosis && detail.diagnosis !== '{}'">
          <strong>结构化诊断：</strong><code>{{ detail.diagnosis }}</code>
        </div>
        <pre class="code-block">{{ detail.content }}</pre>
        <div v-if="detail.ai_result" class="ai-box" v-html="renderMarkdown(detail.ai_result)"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.teacher-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.class-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.class-tab {
  padding: 7px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: white;
  font-size: 13px;
  cursor: pointer;
  color: #475569;
}

.class-tab.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

.class-tab.add {
  border-style: dashed;
  color: #3b82f6;
}

.class-tab .count {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 6px;
}

.class-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.class-head h3 {
  margin: 0 0 4px;
  color: #1e293b;
}

.sub {
  font-size: 12px;
  color: #94a3b8;
}

.invite {
  border: 1px dashed #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 12px;
  cursor: pointer;
}

.invite strong {
  font-family: monospace;
  font-size: 15px;
  letter-spacing: 2px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat {
  background: #f8fafc;
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}

.stat b {
  display: block;
  font-size: 22px;
  color: #1d4ed8;
}

.stat span {
  font-size: 12px;
  color: #94a3b8;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
}

.card h4 {
  margin: 0 0 12px;
  color: #334155;
  font-size: 14px;
}

.progress-row {
  margin-bottom: 10px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
  margin-bottom: 4px;
}

.num {
  color: #94a3b8;
}

.bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.small-bar {
  height: 6px;
  width: 100px;
}

.fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 999px;
}

.error-bar .fill.error {
  background: #f97316;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.table th,
.table td {
  text-align: left;
  padding: 8px 6px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.table th {
  color: #94a3b8;
  font-weight: 500;
  font-size: 12px;
}

.missing {
  color: #b45309;
  font-size: 12px;
}

.diagnosis-cell {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #64748b;
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 10px;
}

.form-grid input,
.form-grid select,
.form-grid textarea {
  padding: 9px 11px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
}

.form-grid textarea {
  grid-column: 1 / -1;
  min-height: 70px;
  resize: vertical;
}

.form-grid button {
  justify-self: start;
  grid-column: 1 / -1;
}

.row {
  display: flex;
  gap: 8px;
}

.row input {
  flex: 1;
  padding: 9px 11px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
}

.row input.short {
  flex: 0 0 160px;
}

.primary {
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
}

.ghost {
  padding: 6px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
}

.assignment-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
  flex-wrap: wrap;
}

.assignment-row:last-child {
  border-bottom: none;
}

.type {
  font-size: 11px;
  background: #eff6ff;
  color: #2563eb;
  padding: 1px 6px;
  border-radius: 4px;
  margin: 0 8px;
}

.kp-chip {
  background: #f1f5f9;
  color: #475569;
  border-radius: 4px;
  padding: 1px 6px;
  font-family: monospace;
  font-size: 11px;
  margin-left: 6px;
}

.empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  padding: 26px 10px;
  background: #f8fafc;
  border-radius: 10px;
}

.empty.small {
  padding: 14px;
  font-size: 12px;
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

.link {
  border: none;
  background: transparent;
  color: #3b82f6;
  cursor: pointer;
  font-size: 12px;
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
  padding: 20px;
}

.modal {
  width: 760px;
  max-height: 85vh;
  overflow-y: auto;
  background: white;
  border-radius: 14px;
  padding: 22px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-head h3 {
  margin: 0;
  font-size: 16px;
  color: #1e293b;
}

.diag-box {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  padding: 10px;
  font-size: 12px;
  color: #9a3412;
  margin: 10px 0;
  word-break: break-all;
}

.code-block {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
}

.ai-box {
  font-size: 13px;
  line-height: 1.7;
  border-top: 1px solid #f1f5f9;
  margin-top: 12px;
  padding-top: 10px;
}

@media (max-width: 820px) {
  .two-col {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
