<script setup>
import { dismiss, toasts } from '../toast.js'
</script>

<template>
  <div class="toast-host">
    <div
      v-for="item in toasts"
      :key="item.id"
      class="toast"
      :class="item.type"
      @click="dismiss(item.id)"
    >
      {{ item.message }}
    </div>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  right: 20px;
  bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 80;
}

.toast {
  min-width: 220px;
  max-width: 380px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: white;
  background: #334155;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2);
  cursor: pointer;
  animation: slide-in 0.18s ease-out;
}

.toast.success {
  background: #16a34a;
}

.toast.error {
  background: #dc2626;
}

.toast.warn {
  background: #d97706;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
