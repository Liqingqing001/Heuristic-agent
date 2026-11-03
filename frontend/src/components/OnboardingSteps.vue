<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { navigateTo, state } from '../session.js'
const props = defineProps({
  teacher: Boolean,
  hasClass: Boolean,
  hasAssignment: Boolean,
})
defineEmits(['open-settings'])
const steps = computed(() =>
  props.teacher
    ? [
        {
          title: '创建班级',
          text: '邀请学生一起学习',
          done: props.hasClass,
          tab: 'workspace',
          action: 'create',
        },
        {
          title: '准备知识库',
          text: '建立课程知识索引',
          done: Object.values(state.status?.knowledge || {}).some((n) => n > 0),
          tab: 'knowledge',
        },
        {
          title: '发布第一个任务',
          text: '让学习有一个起点',
          done: props.hasAssignment,
          tab: 'workspace',
          action: 'publish',
        },
      ]
    : [
        {
          title: '加入班级',
          text: '向老师索取邀请码',
          done: props.hasClass,
          tab: 'homework',
        },
        {
          title: '连接 AI 助教',
          text: '配置个人模型密钥',
          done: !!state.llmKey || !!state.status?.server_key,
          settings: true,
        },
        {
          title: '完成第一个任务',
          text: '开始思考，收获反馈',
          done: props.hasAssignment,
          tab: 'homework',
        },
      ]
)
</script>
<template>
  <section v-if="steps.some((s) => !s.done)" class="onboarding">
    <div class="section-heading">
      <div>
        <span class="eyebrow">QUICK START</span>
        <h3>从这里开始</h3>
      </div>
      <span class="muted"
        >{{ steps.filter((s) => s.done).length }} / 3 已完成</span
      >
    </div>
    <div class="steps">
      <button
        v-for="(step, i) in steps"
        :key="step.title"
        :class="{ complete: step.done }"
        @click="
          () => {
            step.settings
              ? $emit('open-settings')
              : navigateTo(step.tab, { action: step.action })
          }
        "
      >
        <span class="step-number"
          ><AppIcon v-if="step.done" name="check" :size="17" /><template
            v-else
            >{{ i + 1 }}</template
          ></span
        ><span
          ><strong>{{ step.title }}</strong
          ><small>{{ step.text }}</small></span
        ><AppIcon class="step-arrow" name="arrow" :size="17" />
      </button>
    </div>
  </section>
</template>
<style scoped>
.onboarding {
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 22px;
}
.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 18px;
}
.steps button {
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid #e4eaf5;
  border-radius: 10px;
  background: #fafbfe;
  text-align: left;
  padding: 15px 12px;
}
.step-number {
  display: grid;
  place-items: center;
  height: 30px;
  width: 30px;
  background: #eaf0ff;
  color: var(--primary);
  border-radius: 50%;
  font-size: 13px;
  flex-shrink: 0;
}
.steps strong {
  display: block;
  font-size: 13px;
}
.steps small {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}
.complete .step-number {
  background: #e9f6ef;
  color: #16835b;
}
.step-arrow {
  margin-left: auto;
  color: #7a8ba9;
  flex-shrink: 0;
}
@media (max-width: 1000px) {
  .steps {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 760px) {
  .steps .complete {
    display: none;
  }
  .onboarding {
    padding: 18px;
  }
  .steps {
    gap: 8px;
  }
  .steps button {
    padding: 12px;
  }
}
</style>
