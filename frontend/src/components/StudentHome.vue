<script setup>
import { computed, onActivated, ref } from 'vue'
import { listAssignments, listClasses, myMastery } from '../api.js'
import { state, navigateTo } from '../session.js'
import { chapterLabel } from '../kp.js'

import AppIcon from './AppIcon.vue'
import AsyncState from './AsyncState.vue'
import OnboardingSteps from './OnboardingSteps.vue'
import { needsWork, sortAssignments } from '../assignments.js'
const emit = defineEmits(['goto', 'start-assignment', 'open-settings'])
const error = ref('')

const loading = ref(true)
const classes = ref([])
const assignments = ref([])
const mastery = ref([])

const displayName = computed(
  () =>
    state.user?.display_name ||
    state.user?.real_name ||
    state.user?.username ||
    '同学'
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const todos = computed(() =>
  sortAssignments(assignments.value.filter(needsWork))
)
const recent = computed(() =>
  assignments.value
    .filter((item) => item.my_submission)
    .sort((a, b) =>
      String(b.my_submission.submitted_at).localeCompare(
        String(a.my_submission.submitted_at)
      )
    )
    .slice(0, 4)
)
const weakPoints = computed(() =>
  [...mastery.value].sort((a, b) => a.score - b.score).slice(0, 3)
)

const submittedCount = computed(
  () =>
    assignments.value.filter((item) => item.my_submission && !needsWork(item))
      .length
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [data, masteryData] = await Promise.all([listClasses(), myMastery()])
    classes.value = data.joined || []
    const groups = await Promise.all(
      classes.value.map(async (cls) => {
        const items = await listAssignments(cls.id)
        return items.map((item) => ({
          ...item,
          class_name: cls.name,
          class_id: cls.id,
        }))
      })
    )
    assignments.value = groups.flat()
    mastery.value = masteryData.items || []
  } catch (e) {
    error.value = e.message || '学习数据加载失败'
  } finally {
    loading.value = false
  }
}

function formatTime(value) {
  if (!value) return '不限'
  return value.replace('T', ' ')
}

function openAssignment(item) {
  if (item.type === 'code') {
    emit('start-assignment', { ...item, class_name: item.class_name })
  } else {
    navigateTo('homework', { classId: item.class_id, assignmentId: item.id })
  }
}

function statusLabel(item) {
  const status = item.my_submission?.status
  if (status === 'graded') return '已批阅'
  if (status === 'returned') return '已退回'
  return '已提交'
}

onActivated(load)
</script>

<template>
  <AsyncState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="load"
  />

  <div v-else class="home">
    <div class="hello">
      <div class="hero-label">一点点理解，一步步进步</div>
      <h3>{{ greeting }}，{{ displayName }}</h3>
      <p v-if="!classes.length">还没有加入班级，先向老师要一个邀请码。</p>
      <p v-else-if="todos.length">
        还有 {{ todos.length }} 个任务待完成，加油。
      </p>
      <p v-else>任务都完成了，可以去学习助手巩固一下。</p>
      <button
        class="hero-action"
        @click="emit('goto', todos.length ? 'homework' : 'assistant')"
      >
        {{ todos.length ? '继续完成任务' : '开始一次提问' }}
        <AppIcon name="arrow" :size="18" />
      </button>
    </div>

    <div class="stats">
      <div class="stat">
        <span class="stat-icon"><AppIcon name="homework" /></span
        ><b>{{ todos.length }}</b>
        <span>待完成任务</span>
      </div>
      <div class="stat">
        <span class="stat-icon green"><AppIcon name="check" /></span
        ><b>{{ submittedCount }}</b>
        <span>已提交</span>
      </div>
      <div class="stat">
        <span class="stat-icon purple"><AppIcon name="workspace" /></span
        ><b>{{ classes.length }}</b>
        <span>我的班级</span>
      </div>
    </div>

    <OnboardingSteps
      :has-class="!!classes.length"
      :has-assignment="recent.length > 0"
      @open-settings="emit('open-settings')"
    />
    <div class="columns">
      <section class="panel">
        <div class="panel-head">
          <h4>待办任务</h4>
          <button class="link" @click="emit('goto', 'homework')">
            全部任务 →
          </button>
        </div>

        <div v-if="!todos.length" class="empty small">
          没有待办任务。去「作业中心」看看已完成的任务吧。
        </div>

        <div v-for="item in todos.slice(0, 4)" :key="item.id" class="row">
          <div class="row-main">
            <div class="row-title">
              {{ item.title }}
              <span
                v-if="item.my_submission?.status === 'returned'"
                class="badge returned"
                >待重做</span
              >
              <span v-if="item.is_overdue" class="badge overdue">已截止</span>
            </div>
            <div class="row-meta">
              <span>{{ item.class_name }}</span>
              <span>截止 {{ formatTime(item.due_at) }}</span>
            </div>
          </div>
          <button
            class="primary"
            :disabled="item.is_overdue && !item.allow_late"
            @click="openAssignment(item)"
          >
            {{
              item.is_overdue && !item.allow_late
                ? '已截止'
                : item.my_submission?.status === 'returned'
                  ? '去重做'
                  : '去完成'
            }}
          </button>
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
            <strong
              v-if="
                item.my_submission.score !== null &&
                item.my_submission.score !== undefined
              "
              class="score"
            >
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
        <button
          class="weak-title"
          @click="
            () => {
              navigateTo('knowledge', { kpId: item.kp_id, query: item.title })
            }
          "
        >
          <span class="kp">{{ chapterLabel(item.kp_id) }}</span>
          {{ item.title || '未命名知识点' }}
        </button>
        <div
          class="bar"
          role="progressbar"
          :aria-label="item.title"
          :aria-valuenow="item.score"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div class="fill" :style="{ width: `${item.score}%` }"></div>
        </div>
        <span class="weak-score">{{ item.score }}</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hello {
  position: relative;
  padding: 28px 30px !important;
  border-radius: var(--radius);
  background: linear-gradient(110deg, #edf3ff, #e5edfc 70%, #d9e6fc);
  overflow: hidden;
  min-height: 180px;
}
.hello::after {
  content: '?';
  position: absolute;
  right: 38px;
  top: -26px;
  font-size: 200px;
  line-height: 1.2;
  font-weight: 800;
  color: #3264d80b;
  transform: rotate(12deg);
  pointer-events: none;
}
.hero-label {
  font-size: 11px;
  letter-spacing: 2px;
  color: var(--primary);
  margin-bottom: 12px;
}
.hello h3 {
  font-size: 25px !important;
  letter-spacing: -0.5px;
}
.hello p {
  margin-top: 8px !important;
}
.hero-action {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--primary);
  color: white;
  border: 0;
  border-radius: 8px;
  padding: 10px 15px;
  font-size: 12px;
}
.stat {
  position: relative;
  text-align: left !important;
  padding: 20px 22px !important;
  background: white !important;
  border-radius: var(--radius) !important;
}
.stat b {
  color: var(--text) !important;
  font-size: 29px !important;
}
.stat-icon {
  position: absolute;
  right: 20px;
  top: 24px;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #edf2ff;
  color: var(--primary);
}
.stat-icon.green {
  background: #eaf7f1;
  color: #258562;
}
.stat-icon.purple {
  background: #f2edfb;
  color: #8059bf;
}
.panel {
  background: white;
  border-radius: var(--radius) !important;
  padding: 22px !important;
}
.panel-head h4 {
  font-size: 15px !important;
}
.weak-title {
  border: 0;
  background: none;
  text-align: left;
  padding: 0;
  color: var(--primary) !important;
  white-space: normal !important;
}
.fill {
  background: #e4ac5d !important;
}
.home {
  gap: 20px !important;
}
@media (max-width: 760px) {
  .hello {
    padding: 24px 20px !important;
  }
  .hello h3 {
    font-size: 22px !important;
  }
  .stat {
    padding: 14px 12px !important;
  }
  .stat-icon {
    position: static;
    width: 30px;
    height: 30px;
    margin-bottom: 8px;
  }
  .stat b {
    font-size: 25px !important;
  }
  .stat span {
    font-size: 11px !important;
  }
  .stats {
    gap: 8px !important;
  }
  .panel {
    padding: 18px !important;
  }
  .row-meta {
    flex-wrap: wrap;
    gap: 3px 8px !important;
  }
  .weak-row {
    flex-wrap: wrap;
  }
  .weak-title {
    width: 100% !important;
  }
  .panel-head {
    flex-wrap: wrap;
    gap: 6px;
  }
}

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
  color: var(--muted);
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
  color: var(--muted);
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
  color: var(--primary);
  font-size: 12px;
  cursor: pointer;
}

.hint {
  font-size: 12px;
  color: var(--muted);
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
  font-size: 12px;
  color: var(--muted);
}

.row-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  font-size: 12px;
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
  width: 52%;
  font-size: 13px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kp {
  font-family: monospace;
  font-size: 12px;
  color: var(--muted);
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
  background: var(--primary);
  color: white;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}

.empty {
  color: var(--muted);
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
