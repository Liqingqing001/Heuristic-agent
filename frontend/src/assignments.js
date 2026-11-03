export function assignmentStatus(item) {
  const status = item.my_submission?.status
  if (status === 'returned') return 'returned'
  if (status === 'graded') return 'graded'
  if (status) return 'pending'
  return 'todo'
}
export const statusLabels = {
  todo: '待提交',
  returned: '待重做',
  pending: '待批阅',
  graded: '已批阅',
}
export function needsWork(item) {
  return ['todo', 'returned'].includes(assignmentStatus(item))
}
export function sortAssignments(items) {
  return [...items].sort((a, b) => {
    const priority = (item) =>
      assignmentStatus(item) === 'returned' ? 0 : needsWork(item) ? 1 : 2
    return (
      priority(a) - priority(b) ||
      (a.due_at || '9999').localeCompare(b.due_at || '9999')
    )
  })
}
