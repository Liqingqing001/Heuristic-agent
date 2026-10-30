<script setup>
import { computed, onMounted, ref } from 'vue'
import { classMastery, getOverview, listClasses } from '../api.js'
import GradeModal from './GradeModal.vue'

const emit = defineEmits(['goto'])

const loading = ref(true)
const classes = ref([])
const currentId = ref(null)
const overview = ref(null)
const mastery = ref([])
const gradeTarget = ref(null)

const currentClass = computed(
  () => classes.value.find((item) => item.id === currentId.value) || null
)

const averageRate = computed(() => {
  const list = overview.value?.assignments || []
  if (!list.length) return 0
  return Math.round((list.reduce((sum, item) => sum + item.rate, 0) / list.length) * 100)
})

const maxTrend = computed(() => {
  const counts = (overview.value?.trend || []).map((item) => item.count)
  return Math.max(1, ...counts)
})

const pending = computed(() =>
  (overview.value?.recent_submissions || []).filter(
    (item) => item.status === 'submitted' || item.status === 'analyzed'
  )
)

const weakPoints = computed(() => mastery.value.slice(0, 3))

async function load() {
  loading.value = true
  const data = await listClasses()
  classes.value = data.taught || []
  if (classes.value.length) {
    await selectClass(classes.value[0].id)
  }
  loading.value = false
}

async function selectClass(id) {
  currentId.value = id
  const [stats, masteryData] = await Promise.all([getOverview(id), classMastery(id)])
  overview.value = stats
  mastery.value = masteryData.items || []
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

async function onGradeSaved() {
  gradeTarget.value = null
  if (currentId.value) await selectClass(currentId.value)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="empty">加载中…</div>

  <div v-else-if="!classes.length" class="empty">
    还没有班级。<button class="primary" @click="emit('goto', 'workspace')">去创建班级</button>
  </div>

  <div v-else class="home">
    <div class="head">
      <div class="class-tabs">
        <button
          v-for="item in classes"
          :key="item.id"
          :class="{ active: item.id === currentId }"
          @click="selectClass(item.id)"
        >
          {{ item.name }}
        </button>
      </div>
      <button class="primary" @click="emit('goto', 'workspace')">进入班级管理</button>
    </div>

    <div class="stats">
      <div class="stat">
        <b>{{ overview?.member_count ?? 0 }}</b>
        <span>学生人数</span>
      </div>
      <div class="stat">
        <b>{{ overview?.assignment_count ?? 0 }}</b>
        <span>任务数</span>
      </div>
      <div class="stat">
        <b class="warn">{{ overview?.pending_grading ?? 0 }}</b>
        <span>待批阅</span>
      </div>
      <div class="stat">
        <b>{{ averageRate }}%</b>
        <span>平均提交率</span>
      </div>
    </div>

    <div class="columns">
      <section class="panel">
        <div class="panel-head">
          <h4>近 14 天提交趋势</h4>
        </div>
        <div class="chart">
          <div
            v-for="item in overview?.trend || []"
            :key="item.date"
            class="chart-col"
            :title="`${item.date}：${item.count} 次`"
          >
            <div class="chart-bar" :style="{ height: `${Math.round((item.count / maxTrend) * 100)}%` }"></div>
            <span class="chart-label">{{ item.date.slice(5) }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h4>薄弱知识点</h4>
          <span class="hint">按班级平均掌握度从低到高</span>
        </div>
        <div v-if="!weakPoints.length" class="empty small">还没有诊断数据</div>
        <div v-for="item in weakPoints" :key="item.kp_id" class="weak">
          <div class="weak-title">
            <span class="kp">{{ item.kp_id }}</span>
            {{ item.title || '未命名知识点' }}
          </div>
          <div class="bar"><div class="fill" :style="{ width: `${item.avg_score}%` }"></div></div>
          <span class="weak-score">{{ item.avg_score }}</span>
        </div>
      </section>
    </div>

    <section class="panel">
      <div class="panel-head">
        <h4>待批阅</h4>
        <button class="link" @click="emit('goto', 'workspace')">去批阅 →</button>
      </div>
      <div v-if="!pending.length" class="empty small">没有待批阅的提交。</div>
      <div v-for="item in pending.slice(0, 5)" :key="item.id" class="row clickable" @click="gradeTarget = item">
        <div>
          <div class="row-title">{{ item.assignment_title }}</div>
          <div class="row-meta">
            <span>{{ item.username }}</span>
            <span>{{ formatTime(item.submitted_at) }}</span>
          </div>
        </div>
        <span class="badge warn">去批阅</span>
      </div>
    </section>

    <GradeModal
      :target="gradeTarget"
      :assignment-title="gradeTarget?.assignment_title || ''"
      @close="gradeTarget = null"
      @saved="onGradeSaved"
    />
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.class-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.class-tabs button {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: white;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
}

.class-tabs button.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat {
  background: #f8fafc;
  border: 1px solid #e8eef6;
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}

.stat b {
  display: block;
  font-size: 22px;
  color: #1d4ed8;
}

.stat b.warn {
  color: #d97706;
}

.stat span {
  font-size: 12px;
  color: #64748b;
}

.columns {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
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
  margin-bottom: 10px;
}

.panel-head h4 {
  margin: 0;
  font-size: 14px;
  color: #334155;
}

.hint {
  font-size: 11px;
  color: #94a3b8;
}

.chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 120px;
  padding-top: 6px;
}

.chart-col {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
}

.chart-bar {
  width: 100%;
  min-height: 3px;
  background: linear-gradient(180deg, #93c5fd, #3b82f6);
  border-radius: 4px 4px 0 0;
}

.chart-label {
  font-size: 9px;
  color: #cbd5e1;
}

.weak {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
}

.weak-title {
  width: 48%;
  font-size: 12px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kp {
  font-family: monospace;
  font-size: 10px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 5px;
  margin-right: 4px;
}

.bar {
  flex: 1;
  height: 7px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.fill {
  height: 100%;
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.weak-score {
  width: 32px;
  text-align: right;
  font-size: 12px;
  color: #b45309;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid #f1f5f9;
}

.row:last-child {
  border-bottom: none;
}

.row-title {
  font-size: 13px;
  color: #1e293b;
}

.row-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 3px;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  background: #f8fafc;
}

.badge {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
}

.badge.warn {
  background: #fffbeb;
  color: #b45309;
}

.primary {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
}

.link {
  border: none;
  background: transparent;
  color: #3b82f6;
  font-size: 12px;
  cursor: pointer;
}

.empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  padding: 40px;
}

.empty.small {
  padding: 14px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .columns {
    grid-template-columns: 1fr;
  }
}
</style>
