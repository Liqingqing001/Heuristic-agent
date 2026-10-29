<script setup>
import { onMounted, ref } from 'vue'
import {
  joinClass,
  listAssignments,
  listClasses,
  submitTextAnswer,
} from '../api.js'

const emit = defineEmits(['start-assignment'])

const classes = ref([])
const currentId = ref(null)
const assignments = ref([])
const loading = ref(false)
const joinCode = ref('')
const joinError = ref('')
const joining = ref(false)

const answers = ref({})
const submitting = ref({})
const message = ref('')

async function loadClasses() {
  const data = await listClasses()
  classes.value = data.joined || []
  if (!currentId.value && classes.value.length) {
    await selectClass(classes.value[0].id)
  }
}

async function selectClass(id) {
  currentId.value = id
  await loadAssignments()
}

async function loadAssignments() {
  if (!currentId.value) return
  loading.value = true
  assignments.value = await listAssignments(currentId.value)
  loading.value = false
}

async function doJoin() {
  joinError.value = ''
  message.value = ''
  const code = joinCode.value.trim()
  if (!code) {
    joinError.value = '请输入邀请码'
    return
  }
  joining.value = true
  try {
    const result = await joinClass(code)
    message.value = result.status === 'already' ? '你已经在这个班级里了' : '加入成功'
    joinCode.value = ''
    await loadClasses()
    if (result.class) await selectClass(result.class.id)
  } catch (e) {
    joinError.value = e.message || '加入失败'
  } finally {
    joining.value = false
  }
}

function goComplete(assignment) {
  const cls = classes.value.find((item) => item.id === currentId.value)
  emit('start-assignment', {
    ...assignment,
    class_name: cls?.name || '',
  })
}

async function submitAnswer(assignment) {
  const content = (answers.value[assignment.id] || '').trim()
  if (!content) {
    message.value = '请先写下你的答案'
    return
  }
  submitting.value = { ...submitting.value, [assignment.id]: true }
  try {
    await submitTextAnswer(assignment.id, content)
    message.value = '已提交'
    await loadAssignments()
  } catch (e) {
    message.value = e.message || '提交失败'
  } finally {
    submitting.value = { ...submitting.value, [assignment.id]: false }
  }
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

onMounted(loadClasses)
</script>

<template>
  <div class="student-panel">
    <div class="join-row">
      <input v-model="joinCode" placeholder="输入老师给的 6 位班级邀请码" @keydown.enter="doJoin" />
      <button :disabled="joining" @click="doJoin">{{ joining ? '加入中…' : '加入班级' }}</button>
    </div>
    <p v-if="joinError" class="error">{{ joinError }}</p>
    <p v-if="message" class="ok">{{ message }}</p>

    <div v-if="classes.length === 0" class="empty">
      还没有加入任何班级。向老师要一个邀请码，粘贴到上面即可。
    </div>

    <template v-else>
      <div class="class-tabs">
        <button
          v-for="item in classes"
          :key="item.id"
          class="class-tab"
          :class="{ active: item.id === currentId }"
          @click="selectClass(item.id)"
        >
          {{ item.name }}
          <span class="teacher">{{ item.teacher_name }}</span>
        </button>
      </div>

      <div v-if="loading" class="empty">加载任务中…</div>
      <div v-else-if="assignments.length === 0" class="empty">老师还没有发布任务。</div>

      <div v-for="assignment in assignments" :key="assignment.id" class="assignment">
        <div class="assignment-head">
          <div>
            <span class="type" :class="assignment.type">
              {{ assignment.type === 'code' ? '代码' : '问答' }}
            </span>
            <strong>{{ assignment.title }}</strong>
          </div>
          <span
            class="status"
            :class="assignment.my_submission ? 'done' : 'todo'"
          >
            {{ assignment.my_submission ? '已提交' : '未提交' }}
          </span>
        </div>

        <p v-if="assignment.description" class="desc">{{ assignment.description }}</p>

        <div class="meta">
          <span>截止：{{ formatTime(assignment.due_at) }}</span>
          <template v-if="assignment.kp_ids?.length">
            <span
              v-for="kp in assignment.kp_ids"
              :key="kp"
              class="kp-chip"
            >{{ kp }}</span>
          </template>
        </div>

        <div v-if="assignment.type === 'code'" class="actions">
          <button class="primary" @click="goComplete(assignment)">
            {{ assignment.my_submission ? '重新提交' : '去完成' }}
          </button>
          <span v-if="assignment.my_submission" class="hint">
            最近提交：{{ formatTime(assignment.my_submission.submitted_at) }}
          </span>
        </div>

        <div v-else class="actions answer-box">
          <textarea
            v-model="answers[assignment.id]"
            :placeholder="assignment.my_submission ? '已提交过，可修改后重新提交' : '写下你的答案…'"
          ></textarea>
          <button
            class="primary"
            :disabled="submitting[assignment.id]"
            @click="submitAnswer(assignment)"
          >
            {{ submitting[assignment.id] ? '提交中…' : '提交答案' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.student-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.join-row {
  display: flex;
  gap: 8px;
}

.join-row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
}

.join-row input:focus {
  border-color: #3b82f6;
  outline: none;
}

.join-row button {
  padding: 10px 18px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
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

.empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  padding: 30px 10px;
  background: #f8fafc;
  border-radius: 10px;
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

.class-tab .teacher {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 6px;
}

.assignment {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assignment-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.assignment-head strong {
  color: #1e293b;
  font-size: 15px;
}

.type {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 4px;
  margin-right: 8px;
  vertical-align: middle;
}

.type.code {
  background: #eff6ff;
  color: #2563eb;
}

.type.question {
  background: #fef3c7;
  color: #b45309;
}

.status {
  font-size: 12px;
  white-space: nowrap;
}

.status.done {
  color: #15803d;
}

.status.todo {
  color: #b45309;
}

.desc {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #94a3b8;
}

.kp-chip {
  background: #f1f5f9;
  color: #475569;
  border-radius: 4px;
  padding: 1px 6px;
  font-family: monospace;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.answer-box {
  align-items: stretch;
}

.answer-box textarea {
  flex: 1;
  min-height: 80px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  resize: vertical;
}

.primary {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.hint {
  font-size: 12px;
  color: #94a3b8;
}
</style>
