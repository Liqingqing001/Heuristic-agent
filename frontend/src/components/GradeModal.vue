<script setup>
import { ref, watch } from 'vue'
import { gradeSubmission } from '../api.js'
import { toast } from '../toast.js'

const props = defineProps({
  target: { type: Object, default: null },
  assignmentTitle: { type: String, default: '' },
})
const emit = defineEmits(['close', 'saved'])

const form = ref({ score: '', feedback: '', returned: false })
const saving = ref(false)

watch(
  () => props.target,
  (target) => {
    if (target) {
      form.value = {
        score: target.score ?? '',
        feedback: target.feedback || '',
        returned: false,
      }
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
    toast(form.value.returned ? '已退回，学生可以重做' : '批阅已保存', 'success')
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
    <div class="modal">
      <div class="modal-head">
        <h3>批阅：{{ target.display_name || target.username }}</h3>
        <button class="link" @click="emit('close')">关闭</button>
      </div>
      <p class="sub">
        <template v-if="assignmentTitle">「{{ assignmentTitle }}」 · </template>
        {{ formatTime(target.submitted_at) }}
      </p>

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

      <div class="actions">
        <button class="ghost" @click="emit('close')">取消</button>
        <button class="primary" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存批阅' }}
        </button>
      </div>
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
  width: 480px;
  max-width: 100%;
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
  color: #3b82f6;
  font-size: 12px;
  cursor: pointer;
}

.sub {
  margin: 6px 0 0;
  font-size: 12px;
  color: #94a3b8;
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
</style>
