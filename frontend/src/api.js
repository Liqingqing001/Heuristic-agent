// 后端接口封装：Token 注入 + BYOK 密钥透传 + SSE 流式解析
import { getLlmKey } from './session.js'

const TOKEN_KEY = 'zhiyu_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function authHeaders(extra = {}) {
  const headers = { ...extra }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  // BYOK：使用者自己的 key，后端只在本次请求里使用
  const llmKey = getLlmKey()
  if (llmKey) headers['X-LLM-Key'] = llmKey
  return headers
}

function handle401(resp) {
  if (resp.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('auth-expired'))
    return true
  }
  return false
}

async function readError(resp) {
  try {
    const data = await resp.json()
    return data.detail || `HTTP ${resp.status}`
  } catch {
    return `HTTP ${resp.status}`
  }
}

// ==================== 认证 ====================
export async function apiLogin(username, password) {
  const resp = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.detail || '登录失败')
  setToken(data.token)
  return data
}

export async function apiRegister(username, password, role = 'student', displayName = '') {
  const resp = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role, display_name: displayName }),
  })
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.detail || '注册失败')
  setToken(data.token)
  return data
}

export async function apiMe() {
  const resp = await fetch('/api/auth/me', { headers: authHeaders() })
  if (!resp.ok) return null
  return resp.json()
}

export function apiLogout() {
  clearToken()
}

// ==================== 状态 ====================
export async function apiStatus() {
  const resp = await fetch('/api/llm/status')
  if (!resp.ok) return null
  return resp.json()
}

// ==================== SSE 流式 ====================
async function streamFetch(url, body, onToken, onError) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) {
    if (handle401(resp)) return null
    onError(await readError(resp))
    return null
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const meta = {}
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      let obj
      try {
        obj = JSON.parse(payload)
      } catch {
        continue
      }
      if (obj.token) onToken(obj.token)
      else if (obj.error) onError(obj.error)
      else if (obj.done) {
        Object.assign(meta, obj)
        return meta
      } else {
        Object.assign(meta, obj)
      }
    }
  }
  return meta
}

// ==================== 对话 ====================
export function streamChat({ question, conversation_id }, onToken, onError) {
  return streamFetch('/api/chat', { question, conversation_id }, onToken, onError)
}

// ==================== 会话管理 ====================
export async function createConversation(title = '新会话') {
  const resp = await fetch('/api/conversations', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ title }),
  })
  if (handle401(resp)) return null
  return resp.json()
}

export async function listConversations() {
  const resp = await fetch('/api/conversations', { headers: authHeaders() })
  if (handle401(resp)) return []
  return resp.json()
}

export async function getConversationMessages(id) {
  const resp = await fetch(`/api/conversations/${id}/messages`, { headers: authHeaders() })
  if (handle401(resp)) return []
  return resp.json()
}

export async function deleteConversation(id) {
  const resp = await fetch(`/api/conversations/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (handle401(resp)) return null
  return resp.json()
}

// ==================== 代码剖析 ====================
export function streamAnalyze({ code, language, question, assignment_id }, onToken, onError) {
  return streamFetch(
    '/api/code/analyze',
    { code, language, question, assignment_id },
    onToken,
    onError
  )
}

export async function listCodeAnalyses() {
  const resp = await fetch('/api/code/analyses', { headers: authHeaders() })
  if (handle401(resp)) return []
  return resp.json()
}

export async function getCodeAnalysis(id) {
  const resp = await fetch(`/api/code/analyses/${id}`, { headers: authHeaders() })
  if (handle401(resp)) return null
  return resp.json()
}

export async function deleteCodeAnalysis(id) {
  const resp = await fetch(`/api/code/analyses/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (handle401(resp)) return null
  return resp.json()
}

// ==================== 班级 / 任务 / 提交 ====================
export async function listClasses() {
  const resp = await fetch('/api/classes', { headers: authHeaders() })
  if (handle401(resp)) return { taught: [], joined: [] }
  return resp.json()
}

export async function createClass(name, term = '') {
  const resp = await fetch('/api/classes', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ name, term }),
  })
  if (!resp.ok) throw new Error(await readError(resp))
  return resp.json()
}

export async function joinClass(code) {
  const resp = await fetch('/api/classes/join', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ code }),
  })
  if (!resp.ok) throw new Error(await readError(resp))
  return resp.json()
}

export async function listAssignments(classId) {
  const resp = await fetch(`/api/classes/${classId}/assignments`, { headers: authHeaders() })
  if (handle401(resp)) return []
  return resp.json()
}

export async function createAssignment(classId, payload) {
  const resp = await fetch(`/api/classes/${classId}/assignments`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })
  if (!resp.ok) throw new Error(await readError(resp))
  return resp.json()
}

export async function getOverview(classId) {
  const resp = await fetch(`/api/classes/${classId}/overview`, { headers: authHeaders() })
  if (!resp.ok) return null
  return resp.json()
}

export async function listMembers(classId) {
  const resp = await fetch(`/api/classes/${classId}/members`, { headers: authHeaders() })
  if (!resp.ok) return []
  return resp.json()
}

export async function listSubmissions(assignmentId) {
  const resp = await fetch(`/api/assignments/${assignmentId}/submissions`, {
    headers: authHeaders(),
  })
  if (!resp.ok) return []
  return resp.json()
}

export async function getSubmission(id) {
  const resp = await fetch(`/api/submissions/${id}`, { headers: authHeaders() })
  if (!resp.ok) return null
  return resp.json()
}

export async function submitTextAnswer(assignmentId, content) {
  const resp = await fetch(`/api/assignments/${assignmentId}/submit`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ content }),
  })
  if (!resp.ok) throw new Error(await readError(resp))
  return resp.json()
}

// ==================== 知识库 ====================
export async function ingestKnowledge() {
  const resp = await fetch('/api/knowledge/ingest', {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!resp.ok) throw new Error(await readError(resp))
  return resp.json()
}

export async function getKnowledgeStats() {
  const resp = await fetch('/api/knowledge/stats')
  if (!resp.ok) return {}
  return resp.json()
}
