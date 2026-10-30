// 知识点编号是「ds-章节-序号」，学生端不需要看到原始编号，
// 统一转成「第几章 · 标题」这种可读文案；教师端保留编号方便对照文件。
const CHAPTERS = {
  1: '链表',
  2: '栈与队列',
  3: '二叉树与 BST',
  4: 'AVL 树',
  5: '排序',
  6: '查找',
  7: '图',
  8: '线性表',
}

export function parseKpId(kpId) {
  const matched = /^ds-(\d{2})-(\d{2})$/.exec(String(kpId || ''))
  if (!matched) return null
  return { chapter: Number(matched[1]), index: Number(matched[2]) }
}

export function chapterLabel(kpId) {
  const parsed = parseKpId(kpId)
  if (!parsed) return ''
  const name = CHAPTERS[parsed.chapter] || ''
  return name ? `第 ${parsed.chapter} 章 · ${name}` : `第 ${parsed.chapter} 章`
}

export function kpTitle(kp) {
  if (!kp) return ''
  return kp.title || chapterLabel(kp.kp_id) || '未命名知识点'
}
