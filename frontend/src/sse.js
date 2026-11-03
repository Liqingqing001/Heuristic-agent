// SSE 的行可以跨网络分块；CRLF 中的 CR/LF 也可能分开到达。
export async function consumeSse(body, onToken, onError) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  const meta = {}
  let buffer = ''
  let data = []
  let complete = false

  function dispatch() {
    if (!data.length) return false
    const payload = data.join('\n')
    data = []
    let obj
    try {
      obj = JSON.parse(payload)
    } catch {
      return false
    }
    if (obj.token) onToken(obj.token)
    else if (obj.error) onError(obj.error)
    else Object.assign(meta, obj)
    return !!obj.done
  }

  function readLines(final = false) {
    while (buffer.length) {
      const match = /[\r\n]/.exec(buffer)
      if (!match) break
      const end = match.index
      if (!final && buffer[end] === '\r' && end === buffer.length - 1) break
      const line = buffer.slice(0, end)
      const width = buffer.slice(end, end + 2) === '\r\n' ? 2 : 1
      buffer = buffer.slice(end + width)
      if (!line) {
        if (dispatch()) return true
      } else if (line.startsWith('data:')) {
        const value = line.slice(5)
        data.push(value.startsWith(' ') ? value.slice(1) : value)
      }
    }
    return false
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        complete = true
        buffer += decoder.decode()
        readLines(true)
        break
      }
      buffer += decoder.decode(value, { stream: true })
      if (readLines()) break
    }
    return meta
  } finally {
    try {
      if (!complete) await reader.cancel()
    } finally {
      reader.releaseLock()
    }
  }
}
