<script setup>
    import { ref, nextTick, onMounted } from 'vue'
    import { marked } from 'marked'
    import hljs from 'highlight.js'
    import {
        streamAnalyze,
        listCodeAnalyses,
        getCodeAnalysis,
        deleteCodeAnalysis,
    } from '../api.js'

    // 表单状态
    const code = ref('')
    const language = ref('cpp')
    const question = ref('')
    const result = ref('')
    const loading = ref(false)
    const resultBox = ref(null)

    // 历史记录
    const history = ref([])
    const currentId = ref(null)

    // 快捷指令
    const activeAction = ref(null)
    const quickActions = [
        { key: 'syntax', label: '语法检查', prompt: '请帮我检查这段代码的语法错误，不要直接改代码，用提问引导我自己发现。' },
        { key: 'diagnose', label: '代码诊断', prompt: '请帮我诊断这段代码的逻辑错误，不要直接给代码，用反问引导我思考。' },
        { key: 'optimize', label: '代码优化', prompt: '请帮我分析这段代码可以优化的地方，用提问引导我思考。' },
        { key: 'comment', label: '代码注释', prompt: '请引导我思考这段代码应该怎么加注释，而不是直接给我注释好的代码。' }
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
        history.value = await listCodeAnalyses()
    }

    // ---- 会话操作 ----
    function newSession() {
        currentId.value = null
        code.value = ''
        language.value = 'cpp'
        question.value = ''
        result.value = ''
        activeAction.value = null
    }

    async function switchSession(item) {
        const rec = await getCodeAnalysis(item.id)
        if (!rec) return
        currentId.value = rec.id
        code.value = rec.code
        language.value = rec.language
        question.value = rec.question || ''
        result.value = rec.result
        activeAction.value = null
        nextTick(() => highlight())
    }

    async function removeSession(id) {
        if (!confirm('确定删除这条剖析记录吗？')) return
        await deleteCodeAnalysis(id)
        if (currentId.value === id) newSession()
        await loadHistory()
    }

    // ---- Markdown 与高亮 ----
    const renderMarkdown = (text) => marked.parse(text || '')

    function highlight() {
        if (!resultBox.value) return
        resultBox.value.querySelectorAll('pre code').forEach((b) => {
            try { hljs.highlightElement(b) } catch (e) { /* 忽略 */ }
        })
    }

    // ---- 提交剖析 ----
    async function submit() {
        const c = code.value.trim()
        if (!c || loading.value) return

        result.value = ''
        loading.value = true
        currentId.value = null  // 提交后是新记录

        // 合并“模式指令”与“用户补充说明”
        let finalQuestion = ''
        if (activeAction.value) finalQuestion = activeAction.value.prompt
        if (question.value.trim()) {
            finalQuestion += (finalQuestion ? '\n\n用户补充说明：' : '') + question.value.trim()
        }

        let accumulated = ''
        const doneInfo = await streamAnalyze(
            { code: c, language: language.value, question: finalQuestion || null },
            (token) => {
                accumulated += token
                result.value = accumulated
            },
            (err) => {
                accumulated += `\n\n⚠️ 出错：${err}`
                result.value = accumulated
            }
        )

        // 用后端返回的 id 标记当前记录
        if (doneInfo && doneInfo.analysis_id) {
            currentId.value = doneInfo.analysis_id
        }

        loading.value = false
        await loadHistory()
        nextTick(() => highlight())
    }

    onMounted(loadHistory)
</script>

<template>
    <div class="code-layout">
        <!-- 左侧历史记录 -->
        <aside class="conv-sidebar">
            <button class="new-btn" @click="newSession">＋ 新建剖析</button>
            <div class="conv-list">
                <div v-for="h in history"
                     :key="h.id"
                     class="conv-item"
                     :class="{ active: h.id === currentId }"
                     @click="switchSession(h)">
                    <span class="conv-title">{{ h.title }}</span>
                    <button class="conv-del" title="删除" @click.stop="removeSession(h.id)">×</button>
                </div>
                <div v-if="history.length === 0" class="empty-hint small">暂无记录</div>
            </div>
        </aside>

        <!-- 右侧主区域 -->
        <div class="code-main">
            <div class="code-form">
                <textarea v-model="code" placeholder="粘贴你的 C/C++ 代码…"></textarea>

                <div class="quick-actions">
                    <button v-for="action in quickActions"
                            :key="action.key"
                            type="button"
                            class="quick-btn"
                            :class="{ active: activeAction?.key === action.key }"
                            @click="toggleAction(action)">
                        {{ action.label }}
                    </button>
                </div>

                <div class="row">
                    <select v-model="language">
                        <option value="cpp">C++</option>
                        <option value="c">C</option>
                    </select>
                    <input v-model="question" placeholder="（可选）补充你的问题" style="flex: 1;" />
                    <button :disabled="loading || !code.trim()" @click="submit">
                        {{ loading ? '诊断中…' : '开始剖析' }}
                    </button>
                </div>
            </div>

            <div v-if="result" ref="resultBox" class="result-box" v-html="renderMarkdown(result)"></div>
            <div v-else class="empty-hint">
                提交一段代码，助教会先诊断逻辑问题，再用提问引导你自己修复——绝不直接给完整代码。
            </div>
        </div>
    </div>
</template>

<style scoped>
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
        background: #3b82f6;
        color: white;
        font-size: 14px;
        cursor: pointer;
    }

        .new-btn:hover {
            background: #2563eb;
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
        color: #94a3b8;
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
            border-color: #3b82f6;
            color: #2563eb;
            background: #eff6ff;
        }

        .quick-btn.active {
            border-color: #3b82f6;
            background: #3b82f6;
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
            background: #3b82f6;
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
        color: #94a3b8;
        font-size: 13px;
        padding: 20px;
    }

        .empty-hint.small {
            font-size: 12px;
            padding: 10px;
        }
</style>