// 轻量全局提示，替代 alert()
import { reactive } from 'vue'

export const toasts = reactive([])
let seq = 0

export function toast(message, type = 'info', timeout = 3200) {
  const id = ++seq
  toasts.push({ id, message: String(message), type })
  setTimeout(() => dismiss(id), timeout)
}

export function dismiss(id) {
  const index = toasts.findIndex((item) => item.id === id)
  if (index >= 0) toasts.splice(index, 1)
}
