// 后端接口封装：Token 注入 + SSE 流式解析 + 会话 + 代码剖析 + 知识库接口

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

// ==================== 认证接口 ====================
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

export async function apiRegister(username, password) {
    const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
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

// ==================== SSE 流式 ====================
async function streamFetch(url, body, onToken, onError) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
    })
    if (!resp.ok || !resp.body) {
        if (handle401(resp)) return
        onError(`HTTP ${resp.status}`)
        return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop()
        for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith('data:')) continue
            const data = line.slice(5).trim()
            let obj
            try {
                obj = JSON.parse(data)
            } catch {
                continue
            }
            if (obj.token) onToken(obj.token)
            else if (obj.error) onError(obj.error)
            else if (obj.done) return obj
        }
    }
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
export function streamAnalyze({ code, language, question }, onToken, onError) {
    return streamFetch('/api/code/analyze', { code, language, question }, onToken, onError)
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

// ==================== 知识库 ====================
export async function ingestKnowledge() {
    const resp = await fetch('/api/knowledge/ingest', { method: 'POST' })
    return resp.json()
}

export async function getKnowledgeStats() {
    const resp = await fetch('/api/knowledge/stats')
    return resp.json()
}