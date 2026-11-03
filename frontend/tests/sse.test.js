import test from 'node:test'
import assert from 'node:assert/strict'
import { consumeSse } from '../src/sse.js'

function stream(text, bytewise = false) {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({
    start(controller) {
      if (bytewise) for (const byte of bytes) controller.enqueue(Uint8Array.of(byte))
      else controller.enqueue(bytes)
      controller.close()
    },
  })
}

for (const newline of ['\n', '\r\n', '\r']) {
  test(`解析跨字节中文与换行 ${JSON.stringify(newline)}`, async () => {
    const tokens = []
    const errors = []
    const body = stream([
      ': heartbeat', '', 'data: {"conversation_id":7}', '',
      'data: {"token":"指针"}', '', 'data: invalid', '',
      'data: {"error":"稍后再试"}', '',
      'data: {"done":true,"analysis_id":9}', '', '',
    ].join(newline), true)
    const meta = await consumeSse(body, t => tokens.push(t), e => errors.push(e))
    assert.deepEqual(tokens, ['指针'])
    assert.deepEqual(errors, ['稍后再试'])
    assert.deepEqual(meta, { conversation_id: 7, done: true, analysis_id: 9 })
    assert.equal(body.locked, false)
  })
}

test('多行 data 事件；忽略未以空行结束的事件', async () => {
  const tokens = []
  await consumeSse(stream('data: {\ndata: "token":"ok"}\n\ndata: {"token":"incomplete"}'), t => tokens.push(t), assert.fail)
  assert.deepEqual(tokens, ['ok'])
})

test('done 后取消未结束的流并释放锁', async () => {
  let cancelled = false
  const body = new ReadableStream({
    start(c) { c.enqueue(new TextEncoder().encode('data: {"done":true}\n\n')) },
    cancel() { cancelled = true },
  })
  await consumeSse(body, assert.fail, assert.fail)
  assert.equal(cancelled, true)
  assert.equal(body.locked, false)
})

test('回调失败仍释放流', async () => {
  const body = stream('data: {"token":"x"}\n\n')
  await assert.rejects(consumeSse(body, () => { throw new Error('callback') }, assert.fail), /callback/)
  assert.equal(body.locked, false)
})

test('读取失败仍释放锁', async () => {
  const body = new ReadableStream({ start(c) { c.error(new Error('network')) } })
  await assert.rejects(consumeSse(body, assert.fail, assert.fail), /network/)
  assert.equal(body.locked, false)
})
