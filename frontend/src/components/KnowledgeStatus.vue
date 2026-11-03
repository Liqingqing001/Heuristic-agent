<script setup>
import { computed, ref, onMounted, onActivated, nextTick } from 'vue'
import { ingestKnowledge } from '../api.js'
import { state } from '../session.js'
import { toast } from '../toast.js'
import { renderMarkdown } from '../markdown.js'
import AppIcon from './AppIcon.vue'
import AsyncState from './AsyncState.vue'
const API = '/api/knowledge'
const stats = ref({}),
  ingesting = ref(false),
  loading = ref(false),
  error = ref(''),
  statsError = ref('')
const isTeacher = computed(() => state.user?.role === 'teacher')
const viewMode = ref('home'),
  viewTitle = ref(''),
  items = ref([]),
  expandedIndex = ref(null),
  searchQuery = ref('')
let requestId = 0,
  handledNavigation = 0,
  lastCategory = null
const CATEGORIES = [
  {
    key: 'lecture',
    name: '课程讲义',
    desc: '从概念出发，理解数据结构的核心原理',
    icon: 'book',
    color: '#3264d8',
  },
  {
    key: 'solutions',
    name: '解题思路',
    desc: '拆解典型问题，找到分析与求解的路径',
    icon: 'light',
    color: '#bf8939',
  },
  {
    key: 'buglib',
    name: '常见错误',
    desc: '从错误现象出发，练习定位与排查',
    icon: 'bug',
    color: '#c76562',
  },
  {
    key: 'kp',
    statKey: 'kp_points',
    name: '知识点地图',
    desc: '按章节梳理知识，连接概念与应用',
    icon: 'target',
    color: '#34886f',
  },
]
const statCount = (cat) => stats.value[cat.statKey || cat.key] || 0
async function fetchJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`服务暂不可用（${res.status}）`)
  return res.json()
}
async function loadStats() {
  statsError.value = ''
  try {
    stats.value = await fetchJson(`${API}/stats`)
  } catch (e) {
    statsError.value = e.message
  }
}
async function loadItems(url) {
  const request = ++requestId
  loading.value = true
  error.value = ''
  items.value = []
  expandedIndex.value = null
  try {
    const data = await fetchJson(url)
    if (request === requestId) items.value = data.items || []
  } catch (e) {
    if (request === requestId) error.value = e.message || '加载失败，请重试'
  } finally {
    if (request === requestId) loading.value = false
  }
}
async function openCategory(cat) {
  lastCategory = cat
  viewMode.value = 'category'
  viewTitle.value = cat.name
  await loadItems(`${API}/list?category=${cat.key}`)
}
async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  viewMode.value = 'search'
  viewTitle.value = `搜索：${q}`
  await loadItems(`${API}/search?q=${encodeURIComponent(q)}`)
}
function retry() {
  if (viewMode.value === 'search') doSearch()
  else if (lastCategory) openCategory(lastCategory)
}
function goHome() {
  ++requestId
  loading.value = false
  error.value = ''
  viewMode.value = 'home'
  viewTitle.value = ''
  items.value = []
  expandedIndex.value = null
  searchQuery.value = ''
}
function toggleExpand(i) {
  expandedIndex.value = expandedIndex.value === i ? null : i
}
async function rebuild() {
  if (ingesting.value) return
  ingesting.value = true
  try {
    const result = await ingestKnowledge()
    if (result.status === 'error') throw new Error(result.message)
    await loadStats()
    state.status = { ...state.status, knowledge: stats.value }
    toast('知识库已更新，可以开始检索了', 'success')
  } catch (e) {
    toast('建库失败：' + e.message, 'error', 6000)
  } finally {
    ingesting.value = false
  }
}
const preview = (text) => (text || '').replace(/[#*`>\-]/g, '').slice(0, 110)
onMounted(loadStats)
onActivated(async () => {
  const target = state.navigation
  if (target?.tab !== 'knowledge' || target.nonce === handledNavigation) return
  handledNavigation = target.nonce
  if (target.kpId) {
    await openCategory(CATEGORIES.find((c) => c.key === 'kp'))
    const index = items.value.findIndex((i) => i.kp_id === target.kpId)
    if (index >= 0) {
      expandedIndex.value = index
      nextTick(() =>
        document
          .querySelector('.item-card.expanded')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      )
    }
  } else if (target.query) {
    searchQuery.value = target.query
    await doSearch()
  }
})
</script>

<template>
  <div class="kb">
    <div class="kb-intro">
      <span class="eyebrow">KNOWLEDGE LIBRARY</span>
      <h3>让知识，连接起来</h3>
      <p>查一个概念，理清一段思路，找到下一步的方向。</p>
    </div>
    <!-- 顶部：返回 + 搜索 -->
    <div class="kb-header">
      <button v-if="viewMode !== 'home'" class="back-btn" @click="goHome">
        ← 返回
      </button>
      <div class="search-bar">
        <input
          aria-label="搜索知识库"
          v-model="searchQuery"
          placeholder="搜索数据结构名词、Bug 现象……"
          @keydown.enter="doSearch"
        />
        <button @click="doSearch">搜索</button>
      </div>
    </div>

    <AsyncState
      v-if="statsError && viewMode === 'home'"
      :error="statsError"
      @retry="loadStats"
    />
    <!-- 分类卡片 -->
    <div v-if="viewMode === 'home'" class="home">
      <div class="category-grid">
        <div
          v-for="cat in CATEGORIES"
          :key="cat.key"
          class="cat-card"
          role="button"
          tabindex="0"
          @keydown.enter="openCategory(cat)"
          @keydown.space.prevent="openCategory(cat)"
          @click="openCategory(cat)"
        >
          <div
            class="cat-icon"
            :style="{ background: cat.color + '1a', color: cat.color }"
          >
            <AppIcon :name="cat.icon" :size="26" />
          </div>
          <div class="cat-body">
            <div class="cat-name">{{ cat.name }}</div>
            <div class="cat-desc">{{ cat.desc }}</div>
          </div>
          <div class="cat-count">{{ statCount(cat) }} 个索引片段</div>
        </div>
      </div>

      <div class="rebuild-row">
        <button v-if="isTeacher" :disabled="ingesting" @click="rebuild">
          {{ ingesting ? '建库中…' : '重新建库' }}
        </button>
        <span v-else class="rebuild-hint">
          知识库由教师统一建库；内容有更新时可以请老师点一次「重新建库」。
        </span>
      </div>
    </div>

    <!-- 分类/搜索：知识卡片列表 -->
    <div v-else class="list-view">
      <div class="list-title">
        {{ viewTitle }}
        <span class="list-count">{{ items.length }} 条</span>
      </div>

      <AsyncState
        v-if="loading || error"
        :loading="loading"
        :error="error"
        @retry="retry"
      />
      <div v-else-if="items.length === 0" class="empty">没有找到相关内容</div>

      <div v-else class="item-list">
        <div
          v-for="(item, i) in items"
          :key="i"
          class="item-card"
          :class="{ expanded: expandedIndex === i }"
        >
          <button
            class="item-head"
            :aria-expanded="expandedIndex === i"
            :aria-controls="`knowledge-item-${i}`"
            @click="toggleExpand(i)"
          >
            <div class="item-title">{{ item.title }}</div>
            <span v-if="item.category_name" class="item-tag">{{
              item.category_name
            }}</span
            ><span class="expand-label">{{
              expandedIndex === i ? '收起 −' : '阅读 +'
            }}</span>
          </button>
          <div v-if="item.source" class="item-source">📎 {{ item.source }}</div>

          <div
            v-if="expandedIndex === i"
            :id="`knowledge-item-${i}`"
            class="item-content"
            v-html="renderMarkdown(item.content)"
          ></div>
          <div v-else class="item-preview">{{ preview(item.content) }}…</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb {
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 26px !important;
}
.kb-intro {
  margin-bottom: 24px;
}
.kb-intro h3 {
  font-size: 24px;
  letter-spacing: -0.4px;
  margin: 8px 0;
}
.kb-intro p {
  font-size: 13px;
  color: var(--muted);
  margin: 0;
}
.back-btn {
  background: none;
  border: 0;
  white-space: nowrap;
}
.cat-card {
  border-radius: 12px !important;
  padding: 24px !important;
}
.cat-count {
  font-size: 11px !important;
  white-space: nowrap;
}
.item-head {
  display: flex;
  width: 100%;
  background: none;
  border: 0;
  text-align: left;
  padding: 0;
  color: inherit;
  gap: 10px;
  align-items: center;
}
.item-title {
  flex: 1;
}
.expand-label {
  font-size: 12px;
  color: var(--primary);
  white-space: nowrap;
}
.item-card {
  cursor: default !important;
  scroll-margin-top: 20px;
}
.item-content {
  max-height: none !important;
}
.kb .category-grid {
  grid-template-columns: repeat(2, 1fr);
}
.item-source {
  font-size: 11px !important;
}
@media (max-width: 760px) {
  .kb {
    padding: 18px !important;
  }
  .kb-intro h3 {
    font-size: 22px;
  }
  .kb .category-grid {
    grid-template-columns: 1fr;
  }
  .cat-card {
    padding: 18px !important;
    flex-wrap: wrap;
  }
  .cat-count {
    margin-left: 60px;
  }
  .search-bar input {
    min-width: 0;
    font-size: 16px !important;
  }
  .kb-header {
    flex-wrap: wrap;
  }
  .cat-body {
    min-width: 0;
  }
  .search-bar {
    min-width: 0;
  }
  .item-head {
    align-items: flex-start;
  }
}

.kb {
  padding: 4px 0;
}

/* 顶部搜索栏 */
.kb-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.back-btn {
  font-size: 14px;
  color: var(--primary);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
}

.back-btn:hover {
  background: #eff6ff;
}

.search-bar {
  flex: 1;
  display: flex;
  gap: 8px;
}

.search-bar input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}

.search-bar input:focus {
  border-color: var(--primary);
}

.search-bar button {
  padding: 9px 20px;
  border: none;
  border-radius: 8px;
  background: var(--primary);
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.search-bar button:hover {
  background: var(--primary);
}

/* 首页三个分类卡片 */
.category-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.cat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.cat-card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-1px);
}

.cat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.cat-body {
  flex: 1;
}

.cat-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 2px;
}

.cat-desc {
  font-size: 12px;
  color: var(--muted);
}

.cat-count {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.rebuild-row {
  text-align: center;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}

.rebuild-row button {
  padding: 8px 20px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
}

.rebuild-row button:hover:not(:disabled) {
  border-color: var(--primary);
  color: var(--primary);
}

.rebuild-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rebuild-hint {
  font-size: 12px;
  color: var(--muted);
}

/* 分类/搜索列表 */
.list-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-count {
  font-size: 12px;
  color: var(--muted);
  font-weight: 400;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-card {
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  transition: all 0.15s;
}

.item-card:hover {
  border-color: #93c5fd;
  background: #f8fbff;
}

.item-card.expanded {
  border-color: var(--primary);
  background: #f8fbff;
}

.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.item-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.item-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: var(--primary);
  flex-shrink: 0;
}

.item-source {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 8px;
}

.item-preview {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}

.item-content {
  font-size: 13.5px;
  color: #334155;
  line-height: 1.75;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  margin-top: 8px;
}

.item-content :deep(pre) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12.5px;
}

.item-content :deep(code) {
  background: #eef2ff;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: monospace;
}

.item-content :deep(h2),
.item-content :deep(h3) {
  font-size: 14px;
  margin: 10px 0 6px;
  color: #1e293b;
}

.item-content :deep(ul),
.item-content :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.empty {
  text-align: center;
  color: var(--muted);
  font-size: 13px;
  padding: 30px;
}
</style>
