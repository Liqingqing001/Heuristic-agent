<script setup>
import { computed, onMounted, ref } from 'vue'
import { listAssignments, listClasses, myMastery } from '../api.js'
import { state } from '../session.js'

const emit = defineEmits(['goto', 'start-assignment'])

const loading = ref(true)
const classes = ref([])
const assignments = ref([])
const mastery = ref([])

const displayName = computed(
  () => state.user?.display_name || state.user?.real_name || state.user?.username || '同学'
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const todos = computed(() => assignments.value.filter((item) => !item.my_submission))
const recent = computed(() =>
  assignments.value
    .filter((item) => item.my_submission)
    .sort((a, b) => String(b.my_submission.submitted_at).localeCompare(String(a.my_submission.submitted_at)))
    .slice(0, 4)
)
const weakPoints = computed(() =>
  [...mastery.value].sort((a, b) => a.score - b.score).slice(0, 3)
)

const submittedCount = computed(
  () => assignments.value.filter((item) => item.my_submission).length
)

async function load() {
  loading.value = true
  const data = await listClasses()
  classes.value = data.joined || []
  const all = []
  for (const cls of classes.value) {
    const items = await listAssignments(cls.id)
    for (const item of items) {
      all.push({ ...item, class_name: cls.name, class_id: cls.id })
    }
  }
  assignments.value = all
  const masteryData = await myMastery()
  mastery.value = masteryData.items || []
  loading.value = false
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

function openAssignment(item) {
  if (item.type === 'code') {
    emit('start-assignment', { ...item, class_name: item.class_name })
  } else {
    emit('goto', 'homework')
  }
}

function statusLabel(item) {
  const status = item.my_submission?.status
  if (status === 'graded') return '已批阅'
  if (status === 'returned') return '已退回'
  return '已提交'
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="empty">加载中…</div>

  <div v-else class="home">
    <div class="hello">
      <h3>{{ greeting }}，{{ displayName }}</h3>
      <p v-if="!classes.length">还没有加入班级，先向老师要一个邀请码。</p>
      <p v-else-if="todos.length">今天有 {{ todos.length }} 个任务待完成，加油。</p>
      <p v-else>任务都完成了，可以去学习助手巩固一下。</p>
    </div>

    <div class="stats">
      <div class="stat">
        <b>{{ todos.length }}</b>
        <span>待完成任务</span>
      </div>
      <div class="stat">
        <b>{{ submittedCount }}</b>
        <span>已提交</span>
      </div>
      <div class="stat">
        <b>{{ classes.length }}</b>
        <span>我的班级</span>
      </div>
    </div>

    <div class="columns">
      <section class="panel">
        <div class="panel-head">
          <h4>待办任务</h4>
          <button class="link" @click="emit('goto', 'homework')">全部任务 →</button>
        </div>

        <div v-if="!todos.length" class="empty small">
          没有待办任务。去「作业中心」看看已完成的任务吧。
        </div>

        <div v-for="item in todos.slice(0, 4)" :key="item.id" class="row">
          <div class="row-main">
            <div class="row-title">
              {{ item.title }}
              <span v-if="item.is_overdue" class="badge overdue">已截止</span>
            </div>
            <div class="row-meta">
              <span>{{ item.class_name }}</span>
              <span>截止 {{ formatTime(item.due_at) }}</span>
            </div>
          </div>
          <button class="primary" @click="openAssignment(item)">去完成</button>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h4>最近提交</h4>
        </div>

        <div v-if="!recent.length" class="empty small">还没有提交记录。</div>

        <div v-for="item in recent" :key="item.id" class="row">
          <div class="row-main">
            <div class="row-title">{{ item.title }}</div>
            <div class="row-meta">
              <span>{{ item.class_name }}</span>
              <span>{{ formatTime(item.my_submission.submitted_at) }}</span>
            </div>
          </div>
          <div class="row-right">
            <span class="badge" :class="item.my_submission.status">
              {{ statusLabel(item) }}
            </span>
            <strong v-if="item.my_submission.score !== null && item.my_submission.score !== undefined" class="score">
              {{ item.my_submission.score }}
            </strong>
          </div>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h4>我薄弱的知识点</h4>
        <span class="hint">根据每次诊断的提示层级自动累计</span>
      </div>

      <div v-if="!weakPoints.length" class="empty small">
        还没有诊断数据。提交一次作业，系统会自动记录你卡在哪些知识点上。
      </div>

      <div v-for="item in weakPoints" :key="item.kp_id" class="weak-row">
        <div class="weak-title">
          <span class="kp">{{ item.kp_id }}</span>
          {{ item.title || '未命名知识点' }}
        </div>
        <div class="bar">
          <div class="fill" :style="{ width: `${item.score}%` }"></div>
        </div>
        <span class="weak-score">{{ item.score }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hello h3 {
  margin: 0 0 4px;
  color: #1e293b;
  font-size: 18px;
}

.hello p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat {
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}

.stat b {
  display: block;
  font-size: 24px;
  color: #1d4ed8;
}

.stat span {
  font-size: 12px;
  color: #64748b;
}

.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.panel {
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 14px 16px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.panel-head h4 {
  margin: 0;
  font-size: 14px;
  color: #334155;
}

.link {
  border: none;
  background: transparent;
  color: #3b82f6;
  font-size: 12px;
  cursor: pointer;
}

.hint {
  font-size: 12px;
  color: #94a3b8;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #f1f5f9;
}

.row:last-child {
  border-bottom: none;
}

.row-main {
  min-width: 0;
}

.row-title {
  font-size: 13px;
  color: #1e293b;
  margin-bottom: 4px;
}

.row-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #94a3b8;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  white-space: nowrap;
}

.badge.graded {
  background: #f0fdf4;
  color: #15803d;
}

.badge.returned {
  background: #fef2f2;
  color: #b91c1c;
}

.badge.overdue {
  background: #fef2f2;
  color: #b91c1c;
  margin-left: 6px;
}

.score {
  color: #1d4ed8;
  font-size: 15px;
}

.weak-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.weak-title {
  width: 42%;
  font-size: 13px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kp {
  font-family: monospace;
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 5px;
  margin-right: 6px;
}

.bar {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b, #ef4444);
  border-radius: 999px;
}

.weak-score {
  width: 34px;
  text-align: right;
  font-size: 12px;
  color: #b45309;
}

.primary {
  padding: 5px 12px;
  border: none;
  border-radius: 6px;
  background: #3b82f6;
  color: white;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  padding: 30px;
}

.empty.small {
  padding: 16px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .columns {
    grid-template-columns: 1fr;
  }
}
</style>
