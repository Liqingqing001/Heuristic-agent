<script setup>
import { computed, ref, watch } from 'vue'
import { getSubmission, gradeSubmission } from '../api.js'
import { renderMarkdown } from '../markdown.js'
import { toast } from '../toast.js'

const props = defineProps({
  target: { type: Object, default: null },
  assignmentTitle: { type: String, default: '' },
})
const emit = defineEmits(['close', 'saved'])

const form = ref({ score: '', feedback: '', returned: false })
const detail = ref(null)
const loading = ref(false)
const saving = ref(false)

const diagnosis = computed(() => {
  const raw = detail.value?.diagnosis
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (!parsed || !Object.keys(parsed).length) return null
    if (!parsed.error_types?.length && !parsed.kp_ids?.length) return null
    return parsed
  } catch {
    return null
  }
})

watch(
  () => props.target,
  async (target) => {
    if (!target) {
      detail.value = null
      return
    }
    form.value = {
      score: target.score ?? '',
      feedback: target.feedback || '',
      returned: false,
    }
    detail.value = null
    loading.value = true
    try {
      detail.value = await getSubmission(target.id)
      if (detail.value) {
        form.value.score = detail.value.score ?? form.value.score
        form.value.feedback = detail.value.feedback || form.value.feedback
      }
    } catch (e) {
      toast('加载提交内容失败：' + (e.message || e), 'error')
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

function formatTime(value) {
  if (!value) return ''
  return value.replace('T', ' ')
}

async function save() {
  const score = Number(form.value.score)
  if (Number.isNaN(score) || score < 0 || score > 100) {
    toast('分数要在 0-100 之间', 'error')
    return
  }
  saving.value = true
  try {
    await gradeSubmission(props.target.id, {
      score,
      feedback: form.value.feedback,
      returned: form.value.returned,
    })
    toast(
      form.value.returned ? '已退回，学生可以重做' : '批阅已保存',
      'success'
    )
    emit('saved')
  } catch (e) {
    toast(e.message || '批阅失败', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="target" class="mask" @click.self="emit('close')">
    <div class="modal" v-dialog="() => emit('close')">
      <div class="modal-head">
        <h3>批阅：{{ target.display_name || target.username }}</h3>
        <button class="link" @click="emit('close')">关闭</button>
      </div>
      <p class="sub">
        <template v-if="assignmentTitle">「{{ assignmentTitle }}」 · </template>
        {{ formatTime(target.submitted_at) }}
      </p>

      <div v-if="loading" class="loading">加载学生提交…</div>

      <template v-else-if="detail">
        <section class="block">
          <div class="block-head">
            <h4>学生提交</h4>
            <span class="tag" :class="detail.language">
              {{ detail.language === 'text' ? '文字回答' : '代码' }}
            </span>
          </div>
          <pre v-if="detail.language !== 'text'" class="code">{{
            detail.content
          }}</pre>
          <div v-else class="answer">{{ detail.content }}</div>
        </section>

        <section v-if="diagnosis" class="block">
          <div class="block-head"><h4>AI 诊断</h4></div>
          <div class="chips">
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
          <details v-if="detail.ai_result" class="ai">
            <summary>展开 AI 诊断全文</summary>
            <div
              class="ai-body"
              v-html="renderMarkdown(detail.ai_result)"
            ></div>
          </details>
        </section>

        <section class="block">
          <div class="block-head"><h4>评分与评语</h4></div>
          <label class="field">
            <span>分数（0-100）</span>
            <input v-model="form.score" type="number" min="0" max="100" />
          </label>
          <label class="field">
            <span>评语（会显示给学生）</span>
            <textarea
              v-model="form.feedback"
              maxlength="500"
              placeholder="指出问题、给下一步建议，最多 500 字…"
            ></textarea>
          </label>
          <label class="check">
            <input v-model="form.returned" type="checkbox" />
            退回重做（学生可再次提交，当前分数会被清除）
          </label>
        </section>

        <div class="actions">
          <button class="ghost" @click="emit('close')">取消</button>
          <button class="primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存批阅' }}
          </button>
        </div>
      </template>

      <div v-else class="loading">没有找到这份提交</div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 45;
  padding: 20px;
}

.modal {
  width: 720px;
  max-width: 100%;
  max-height: 88vh;
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

.link {
  border: none;
  background: transparent;
  color: var(--primary);
  font-size: 12px;
  cursor: pointer;
}

.sub {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.loading {
  padding: 30px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.block {
  margin-top: 16px;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}

.block-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.block-head h4 {
  margin: 0;
  font-size: 13px;
  color: #334155;
}

.tag {
  font-size: 12px;
  padding: 1px 7px;
  border-radius: 4px;
  background: #eff6ff;
  color: var(--primary);
}

.tag.text {
  background: #fef3c7;
  color: #b45309;
}

.code {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.6;
  max-height: 220px;
}

.answer {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
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

.ai {
  margin-top: 10px;
  font-size: 12px;
  color: #475569;
}

.ai summary {
  cursor: pointer;
  color: var(--primary);
}

.ai-body {
  margin-top: 8px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.7;
  max-height: 220px;
  overflow-y: auto;
}

.ai-body :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
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
  min-height: 80px;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  border-color: var(--primary);
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

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.primary {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: var(--primary);
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
</style>
