<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  classMastery,
  createAssignment,
  createClass,
  deleteAssignment,
  exportScores,
  getOverview,
  getStudentDetail,
  getSubmission,
  gradeSubmission,
  listAssignments,
  listClasses,
  listSubmissions,
  updateAssignment,
} from '../api.js'
import { toast } from '../toast.js'
import { renderMarkdown } from '../markdown.js'
import GradeModal from './GradeModal.vue'

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
  allow_late: true,
})
const editingId = ref(null)

const submissions = ref([])
const submissionsTitle = ref('')
const submissionsAssignmentId = ref(null)
const detail = ref(null)

const mastery = ref([])
const gradeTarget = ref(null)
const studentDetail = ref(null)
const studentLoading = ref(false)

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
  const [items, stats, masteryData] = await Promise.all([
    listAssignments(id),
    getOverview(id),
    classMastery(id),
  ])
  assignments.value = items
  overview.value = stats
  mastery.value = masteryData.items || []
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

function normalizeDue(value) {
  const text = (value || '').trim()
  if (!text) return null
  // 支持 2026-12-01 23:59 / 2026/12/01 23:59 / 2026-12-01T23:59
  const normalized = text.replace(/\//g, '-').replace(' ', 'T')
  const matched = normalized.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{1,2}):(\d{2})$/)
  if (!matched) return NaN
  const [, year, month, day, hour, minute] = matched
  return `${year}-${month}-${day}T${hour.padStart(2, '0')}:${minute}`
}

function resetAssignmentForm() {
  editingId.value = null
  newAssignment.value = {
    title: '',
    description: '',
    type: 'code',
    kp_ids: '',
    due_at: '',
    allow_late: true,
  }
}

function startEdit(assignment) {
  editingId.value = assignment.id
  newAssignment.value = {
    title: assignment.title,
    description: assignment.description || '',
    type: assignment.type,
    kp_ids: (assignment.kp_ids || []).join(', '),
    due_at: (assignment.due_at || '').replace('T', ' '),
    allow_late: !!assignment.allow_late,
  }
  message.value = '正在编辑任务，改完点「保存修改」'
}

async function doCreateAssignment() {
  error.value = ''
  const due = normalizeDue(newAssignment.value.due_at)
  if (Number.isNaN(due)) {
    error.value = '截止时间格式应为「2026-12-01 23:59」，也可以留空'
    return
  }
  const payload = {
    title: newAssignment.value.title.trim(),
    description: newAssignment.value.description.trim(),
    type: newAssignment.value.type,
    kp_ids: newAssignment.value.kp_ids
      .split(/[,，\s]+/)
      .map((item) => item.trim())
      .filter(Boolean),
    due_at: due,
    allow_late: !!newAssignment.value.allow_late,
  }
  if (!payload.title) {
    error.value = '任务标题不能为空'
    return
  }
  try {
    if (editingId.value) {
      await updateAssignment(editingId.value, payload)
      toast('任务已更新', 'success')
    } else {
      await createAssignment(currentId.value, payload)
      toast('任务已发布', 'success')
    }
    resetAssignmentForm()
    await selectClass(currentId.value)
  } catch (e) {
    error.value = e.message || '保存失败'
  }
}

async function removeAssignment(assignment) {
  if (!confirm(`确定删除任务「${assignment.title}」？该任务的提交记录也会一起删除。`)) return
  try {
    await deleteAssignment(assignment.id)
    toast('任务已删除', 'success')
    if (submissionsAssignmentId.value === assignment.id) {
      submissions.value = []
      submissionsAssignmentId.value = null
    }
    await selectClass(currentId.value)
  } catch (e) {
    toast(e.message || '删除失败', 'error')
  }
}

async function openSubmissions(assignment) {
  submissionsTitle.value = assignment.title
  submissionsAssignmentId.value = assignment.id
  submissions.value = await listSubmissions(assignment.id)
}

async function openDetail(item) {
  detail.value = await getSubmission(item.id)
}

function closeDetail() {
  detail.value = null
}

function openGrade(item) {
  gradeTarget.value = item
}

async function onGradeSaved() {
  gradeTarget.value = null
  await selectClass(currentId.value)
  if (submissionsAssignmentId.value) {
    submissions.value = await listSubmissions(submissionsAssignmentId.value)
  }
}

async function openStudent(student) {
  studentLoading.value = true
  try {
    studentDetail.value = await getStudentDetail(currentId.value, student.user_id)
  } catch (e) {
    toast(e.message || '加载学生信息失败', 'error')
  } finally {
    studentLoading.value = false
  }
}

async function doExport() {
  try {
    await exportScores(currentId.value)
    toast('成绩单已开始下载（Excel 可直接打开）', 'success')
  } catch (e) {
    toast(e.message || '导出失败', 'error')
  }
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

function statusText(status) {
  const map = {
    submitted: '已提交',
    analyzed: '已诊断',
    graded: '已批阅',
    returned: '已退回',
  }
  return map[status] || status
}



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
        <div class="head-actions">
          <button class="ghost" @click="doExport">导出成绩 CSV</button>
          <button class="invite" @click="copyCode">
            邀请码 <strong>{{ currentClass.code }}</strong>（点击复制）
          </button>
        </div>
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

      <div class="card">
        <h4>知识点掌握度（班级平均）</h4>
        <div v-if="!mastery.length" class="empty small">
          还没有诊断数据（学生提交作业后自动累计）
        </div>
        <div v-for="item in mastery.slice(0, 5)" :key="item.kp_id" class="progress-row">
          <div class="progress-label">
            <span><span class="kp-chip">{{ item.kp_id }}</span>{{ item.title || '未命名知识点' }}</span>
            <span class="num">{{ item.avg_score }}</span>
          </div>
          <div class="bar">
            <div class="fill mastery" :style="{ width: `${item.avg_score}%` }"></div>
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
            <tr
              v-for="student in overview.students"
              :key="student.user_id"
              class="clickable"
              @click="openStudent(student)"
            >
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
          <div class="due-field">
            <input v-model="newAssignment.due_at" placeholder="截止时间：2026-12-01 23:59（可留空）" />
            <span class="due-hint">格式：年-月-日 时:分</span>
          </div>
          <textarea v-model="newAssignment.description" placeholder="任务说明（可选）"></textarea>
          <label class="late-check">
            <input v-model="newAssignment.allow_late" type="checkbox" />
            允许截止后提交（不勾选则到期后禁止提交）
          </label>
          <div class="form-actions">
            <button class="primary" @click="doCreateAssignment">
              {{ editingId ? '保存修改' : '发布' }}
            </button>
            <button v-if="editingId" class="ghost" @click="resetAssignmentForm">取消编辑</button>
            <span v-if="editingId" class="editing-hint">正在编辑：{{ newAssignment.title }}</span>
          </div>
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
          <div class="row-actions">
            <button class="ghost" @click="openSubmissions(item)">
              查看提交（{{ item.submitted_count }}）
            </button>
            <button class="link" @click="startEdit(item)">编辑</button>
            <button class="link danger" @click="removeAssignment(item)">删除</button>
          </div>
        </div>
      </div>

      <div v-if="submissions.length" class="card">
        <h4>「{{ submissionsTitle }}」的提交</h4>
        <table class="table">
          <thead>
            <tr><th>学生</th><th>时间</th><th>状态</th><th>分数</th><th>诊断</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in submissions" :key="item.id">
              <td>{{ item.display_name || item.username }}</td>
              <td>{{ formatTime(item.submitted_at) }}</td>
              <td>{{ statusText(item.status) }}</td>
              <td>{{ item.score ?? '-' }}</td>
              <td class="diagnosis-cell">{{ item.diagnosis }}</td>
              <td class="actions-cell">
                <button class="link" @click="openDetail(item)">查看</button>
                <button class="link" @click="openGrade(item)">批阅</button>
              </td>
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

    <GradeModal
      :target="gradeTarget"
      :assignment-title="submissionsTitle"
      @close="gradeTarget = null"
      @saved="onGradeSaved"
    />

    <div v-if="studentDetail" class="mask" @click.self="studentDetail = null">
      <div class="modal">
        <div class="modal-head">
          <h3>
            {{ studentDetail.profile.display_name || studentDetail.profile.username }}
            <span class="sub-inline">{{ studentDetail.profile.real_name || '' }}</span>
          </h3>
          <button class="link" @click="studentDetail = null">关闭</button>
        </div>
        <p class="sub">
          {{ studentDetail.profile.username }}
          <template v-if="studentDetail.profile.major"> · {{ studentDetail.profile.major }}</template>
          <template v-if="studentDetail.profile.enrollment_year"> · {{ studentDetail.profile.enrollment_year }} 级</template>
        </p>

        <h4 class="block-title">知识点掌握度</h4>
        <div v-if="!studentDetail.mastery.length" class="empty small">还没有诊断数据</div>
        <div v-for="item in studentDetail.mastery" :key="item.kp_id" class="progress-row">
          <div class="progress-label">
            <span>{{ item.title || item.kp_id }}</span>
            <span class="num">{{ item.score }}</span>
          </div>
          <div class="bar"><div class="fill mastery" :style="{ width: `${item.score}%` }"></div></div>
        </div>

        <h4 class="block-title">提交记录</h4>
        <div v-if="!studentDetail.submissions.length" class="empty small">还没有提交</div>
        <table v-else class="table">
          <thead><tr><th>任务</th><th>时间</th><th>状态</th><th>分数</th><th></th></tr></thead>
          <tbody>
            <tr v-for="item in studentDetail.submissions" :key="item.id">
              <td>{{ item.assignment_title }}</td>
              <td>{{ formatTime(item.submitted_at) }}</td>
              <td>{{ statusText(item.status) }}</td>
              <td>{{ item.score ?? '-' }}</td>
              <td>
                <button class="link" @click="openGrade(item); studentDetail = null">批阅</button>
              </td>
            </tr>
          </tbody>
        </table>
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

.due-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.due-field input {
  width: 100%;
}

.due-hint {
  font-size: 11px;
  color: #94a3b8;
}

.form-actions {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.late-check {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.editing-hint {
  font-size: 12px;
  color: #b45309;
}

.head-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.row-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.link.danger {
  color: #ef4444;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  background: #f8fafc;
}

.block-title {
  margin: 18px 0 8px;
  font-size: 13px;
  color: #334155;
}

.sub-inline {
  font-size: 12px;
  color: #94a3b8;
  margin-left: 6px;
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

.small-modal {
  width: 480px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
  font-size: 12px;
  color: #475569;
}

.field input,
.field textarea {
  padding: 9px 11px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  font-size: 13px;
}

.field textarea {
  min-height: 90px;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  border-color: #3b82f6;
  outline: none;
}

.check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin-top: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.primary {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
}

.primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.ghost {
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
}

.actions-cell {
  white-space: nowrap;
}

.actions-cell .link + .link {
  margin-left: 8px;
}

.fill.mastery {
  background: linear-gradient(90deg, #34d399, #3b82f6);
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
