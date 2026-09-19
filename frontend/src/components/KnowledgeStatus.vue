<script setup>
    import { ref, onMounted } from 'vue'
    import { marked } from 'marked'

    const API = '/api/knowledge'

    const stats = ref({ lecture: 0, solutions: 0, buglib: 0 })
    const ingesting = ref(false)
    const loading = ref(false)

    // 视图：'home' | 'category' | 'search'
    const viewMode = ref('home')
    const viewTitle = ref('')
    const items = ref([])
    const expandedIndex = ref(null)
    const searchQuery = ref('')

    const CATEGORIES = [
        { key: 'lecture', name: '讲义', desc: '数据结构核心知识点讲解', icon: '📘', color: '#3b82f6' },
        { key: 'solutions', name: '题解', desc: '典型题目的解题思路与伪代码', icon: '💡', color: '#f59e0b' },
        { key: 'buglib', name: 'Bug 库', desc: '高频错误现象、原因与定位', icon: '🐛', color: '#ef4444' },
    ]

    async function loadStats() {
        try {
            const res = await fetch(`${API}/stats`)
            stats.value = await res.json()
        } catch (e) {
            console.error(e)
        }
    }

    async function openCategory(cat) {
        viewMode.value = 'category'
        viewTitle.value = cat.name
        loading.value = true
        expandedIndex.value = null
        try {
            const res = await fetch(`${API}/list?category=${cat.key}`)
            const data = await res.json()
            items.value = data.items || []
        } catch (e) {
            items.value = []
        }
        loading.value = false
    }

    async function doSearch() {
        const q = searchQuery.value.trim()
        if (!q) return
        viewMode.value = 'search'
        viewTitle.value = `搜索：${q}`
        loading.value = true
        expandedIndex.value = null
        try {
            const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}`)
            const data = await res.json()
            items.value = data.items || []
        } catch (e) {
            items.value = []
        }
        loading.value = false
    }

    function goHome() {
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
            await fetch(`${API}/ingest`, { method: 'POST' })
            await loadStats()
            alert('建库完成')
        } catch (e) {
            alert('建库失败：' + e)
        }
        ingesting.value = false
    }

    const renderMarkdown = (text) => marked.parse(text || '')
    const preview = (text) => (text || '').replace(/[#*`>\-]/g, '').slice(0, 90)

    onMounted(loadStats)
</script>

<template>
    <div class="kb">
        <!-- 顶部：返回 + 搜索 -->
        <div class="kb-header">
            <div v-if="viewMode !== 'home'" class="back-btn" @click="goHome">← 返回</div>
            <div class="search-bar">
                <input v-model="searchQuery"
                       placeholder="搜索数据结构名词、Bug 现象……"
                       @keydown.enter="doSearch" />
                <button @click="doSearch">搜索</button>
            </div>
        </div>

        <!-- 首页：三个分类卡片 -->
        <div v-if="viewMode === 'home'" class="home">
            <div class="category-grid">
                <div v-for="cat in CATEGORIES"
                     :key="cat.key"
                     class="cat-card"
                     @click="openCategory(cat)">
                    <div class="cat-icon" :style="{ background: cat.color + '1a', color: cat.color }">
                        {{ cat.icon }}
                    </div>
                    <div class="cat-body">
                        <div class="cat-name">{{ cat.name }}</div>
                        <div class="cat-desc">{{ cat.desc }}</div>
                    </div>
                    <div class="cat-count">{{ stats[cat.key] || 0 }} 条</div>
                </div>
            </div>

            <div class="rebuild-row">
                <button :disabled="ingesting" @click="rebuild">
                    {{ ingesting ? '建库中…' : '重新建库' }}
                </button>
            </div>
        </div>

        <!-- 分类/搜索：知识卡片列表 -->
        <div v-else class="list-view">
            <div class="list-title">
                {{ viewTitle }}
                <span class="list-count">{{ items.length }} 条</span>
            </div>

            <div v-if="loading" class="empty">加载中…</div>
            <div v-else-if="items.length === 0" class="empty">没有找到相关内容</div>

            <div v-else class="item-list">
                <div v-for="(item, i) in items"
                     :key="i"
                     class="item-card"
                     :class="{ expanded: expandedIndex === i }"
                     @click="toggleExpand(i)">
                    <div class="item-head">
                        <div class="item-title">{{ item.title }}</div>
                        <div v-if="item.category_name" class="item-tag">{{ item.category_name }}</div>
                    </div>
                    <div v-if="item.source" class="item-source">📎 {{ item.source }}</div>

                    <div v-if="expandedIndex === i" class="item-content" v-html="renderMarkdown(item.content)"></div>
                    <div v-else class="item-preview">{{ preview(item.content) }}…</div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
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
        color: #3b82f6;
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
                border-color: #3b82f6;
            }

        .search-bar button {
            padding: 9px 20px;
            border: none;
            border-radius: 8px;
            background: #3b82f6;
            color: white;
            font-size: 14px;
            cursor: pointer;
        }

            .search-bar button:hover {
                background: #2563eb;
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
            border-color: #3b82f6;
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
        color: #94a3b8;
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
                border-color: #3b82f6;
                color: #2563eb;
            }

            .rebuild-row button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
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
        color: #94a3b8;
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
            border-color: #3b82f6;
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
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 999px;
        background: #eff6ff;
        color: #2563eb;
        flex-shrink: 0;
    }

    .item-source {
        font-size: 11px;
        color: #94a3b8;
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
        color: #94a3b8;
        font-size: 13px;
        padding: 30px;
    }
</style>