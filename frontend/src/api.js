// 后端接口封装：SSE 流式解析 + 会话 + 知识库接口

// 解析 SSE：每帧为 "data: {json}\n\n"；返回 done 帧的对象（含 conversation_id）
async function streamFetch(url, body, onToken, onError) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok || !resp.body) {
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

// —— 对话（持久化到后端 SQLite）——
export function streamChat({ question, conversation_id }, onToken, onError) {
  return streamFetch('/api/chat', { question, conversation_id }, onToken, onError)
}

// —— 会话管理 ——
export async function createConversation(title = '新会话') {
  const resp = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return resp.json()
}

export async function listConversations() {
  const resp = await fetch('/api/conversations')
  return resp.json()
}

export async function getConversationMessages(id) {
  const resp = await fetch(`/api/conversations/${id}/messages`)
  return resp.json()
}

export async function deleteConversation(id) {
  const resp = await fetch(`/api/conversations/${id}`, { method: 'DELETE' })
  return resp.json()
}

// —— 代码剖析 ——
export function streamAnalyze({ code, language, question }, onToken, onError) {
  return streamFetch('/api/code/analyze', { code, language, question }, onToken, onError)
}

// —— 知识库 ——
export async function ingestKnowledge() {
  const resp = await fetch('/api/knowledge/ingest', { method: 'POST' })
  return resp.json()
}

export async function getKnowledgeStats() {
  const resp = await fetch('/api/knowledge/stats')
  return resp.json()
}
