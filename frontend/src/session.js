// 全局会话状态：登录用户、个人模型密钥、当前正在完成的任务。
// 密钥只存在浏览器本地（默认 sessionStorage，勾选"记住"才写 localStorage），
// 请求时由后端透传给模型厂商，不落库、不写日志。
import { reactive } from 'vue'

const LLM_KEY = 'zhiyu_llm_key'

export const state = reactive({
  user: null,
  activeAssignment: null,
  status: null,
  llmKey: '',
  remember: false,
})

export function loadLlmKey() {
  const remembered = localStorage.getItem(LLM_KEY) || ''
  const sessionValue = sessionStorage.getItem(LLM_KEY) || ''
  state.llmKey = remembered || sessionValue
  state.remember = !!remembered
  return state.llmKey
}

export function getLlmKey() {
  return state.llmKey || sessionStorage.getItem(LLM_KEY) || localStorage.getItem(LLM_KEY) || ''
}

export function saveLlmKey(key, remember) {
  const value = (key || '').trim()
  state.llmKey = value
  state.remember = !!remember
  sessionStorage.removeItem(LLM_KEY)
  localStorage.removeItem(LLM_KEY)
  if (!value) return
  if (remember) localStorage.setItem(LLM_KEY, value)
  else sessionStorage.setItem(LLM_KEY, value)
}

export function clearLlmKey() {
  saveLlmKey('', false)
}

export function setUser(user) {
  state.user = user
}

export function startAssignment(assignment) {
  state.activeAssignment = assignment
}

export function clearAssignment() {
  state.activeAssignment = null
}
