<script setup>
defineProps({
  loading: Boolean,
  error: { type: String, default: '' },
  empty: { type: String, default: '' },
})
defineEmits(['retry'])
</script>
<template>
  <div
    v-if="loading"
    class="async-skeleton"
    role="status"
    aria-label="正在加载"
  >
    <span></span><span></span><span></span>
    <p>正在加载，请稍候…</p>
  </div>
  <div v-else-if="error" class="async-error" role="alert">
    <strong>暂时无法加载</strong>
    <p>{{ error }}</p>
    <button class="ui-button" @click="$emit('retry')">重新加载</button>
  </div>
  <div v-else-if="empty" class="async-empty">
    <strong>{{ empty }}</strong
    ><slot />
  </div>
</template>
