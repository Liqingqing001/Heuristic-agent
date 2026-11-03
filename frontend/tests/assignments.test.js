import test from 'node:test'
import assert from 'node:assert/strict'
import {
  assignmentStatus,
  needsWork,
  sortAssignments,
} from '../src/assignments.js'

test('提交状态与待办语义一致，退回任务需要重做', () => {
  assert.equal(assignmentStatus({}), 'todo')
  for (const status of ['submitted', 'analyzed'])
    assert.equal(assignmentStatus({ my_submission: { status } }), 'pending')
  assert.equal(needsWork({ my_submission: { status: 'returned' } }), true)
  assert.equal(needsWork({ my_submission: { status: 'graded' } }), false)
})
test('退回任务优先，其次按截止日期排序，且不修改原始列表', () => {
  const items = [
    { id: 1 },
    { id: 2, due_at: '2026-12-01' },
    { id: 3, my_submission: { status: 'returned' } },
    { id: 4, my_submission: { status: 'graded' } },
  ]
  assert.deepEqual(
    sortAssignments(items).map((a) => a.id),
    [3, 2, 1, 4]
  )
  assert.deepEqual(
    items.map((a) => a.id),
    [1, 2, 3, 4]
  )
})
