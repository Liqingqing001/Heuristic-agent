import { test, expect } from '@playwright/test'

let teacher, student, classroom, question, code
const password = 'test123456'
const auth = (user) => ({ Authorization: `Bearer ${user.token}` })
async function json(response) {
  expect(response.ok(), await response.text()).toBeTruthy()
  return response.json()
}

test.beforeAll(async ({ request }) => {
  const suffix = Date.now().toString(36)
  teacher = await json(
    await request.post('/api/auth/register', {
      data: {
        username: `ui_t_${suffix}`,
        password,
        role: 'teacher',
        display_name: '界面测试教师',
      },
    })
  )
  student = await json(
    await request.post('/api/auth/register', {
      data: {
        username: `ui_s_${suffix}`,
        password,
        role: 'student',
        display_name: '界面测试学生',
      },
    })
  )
  classroom = await json(
    await request.post('/api/classes', {
      headers: auth(teacher),
      data: { name: '界面回归测试班' },
    })
  )
  await json(
    await request.post('/api/classes/join', {
      headers: auth(student),
      data: { code: classroom.code },
    })
  )
  question = await json(
    await request.post(`/api/classes/${classroom.id}/assignments`, {
      headers: auth(teacher),
      data: { title: '理解栈和队列', type: 'question', kp_ids: ['ds-02-01'] },
    })
  )
  code = await json(
    await request.post(`/api/classes/${classroom.id}/assignments`, {
      headers: auth(teacher),
      data: { title: '检查链表指针', type: 'code', kp_ids: ['ds-01-02'] },
    })
  )
  await json(
    await request.post(`/api/assignments/${question.id}/submit`, {
      headers: auth(student),
      data: { content: '栈后进先出，队列先进先出' },
    })
  )
})

async function login(page, user = student, tab = 'home') {
  await page.goto('/')
  await page.evaluate(
    (token) => localStorage.setItem('zhiyu_token', token),
    user.token
  )
  await page.goto(`/#/${tab}`)
  await page.reload()
  await expect(page.locator('.shell')).toBeVisible()
}
const desktopTab = (page, name) =>
  page
    .getByRole('navigation', { name: '主要导航' })
    .getByRole('button', { name, exact: true })

test('登录表单标签、密码显隐和真实登录', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('用户名', { exact: true }).fill(student.username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '显示', exact: true }).click()
  await expect(page.getByLabel('密码', { exact: true })).toHaveAttribute(
    'type',
    'text'
  )
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.locator('.hello')).toBeVisible()
})

test('主页面和助手模式切换保留草稿，编辑器延迟加载', async ({ page }) => {
  const assets = []
  page.on('request', (req) => assets.push(req.url()))
  await login(page)
  await expect(page.locator('.hello')).toBeVisible()
  expect(assets.some((url) => /editor-core/.test(url))).toBeFalsy()
  await desktopTab(page, '学习助手').click()
  await page.getByLabel('你的问题', { exact: true }).fill('需要保留的聊天草稿')
  await page.getByRole('button', { name: '代码诊断', exact: true }).click()
  await page.locator('.cm-content').fill('int main() { return 0; }')
  await desktopTab(page, '作业中心').click()
  await desktopTab(page, '学习助手').click()
  await expect(page.locator('.cm-content')).toHaveText(
    'int main() { return 0; }'
  )
  await page.getByRole('button', { name: '对话提问', exact: true }).click()
  await expect(page.getByLabel('你的问题', { exact: true })).toHaveValue(
    '需要保留的聊天草稿'
  )
})

test('退回重做进入首页待办，问答任务可直接定位并保留答案草稿', async ({
  page,
  request,
}) => {
  const submissions = await json(
    await request.get(`/api/assignments/${question.id}/submissions`, {
      headers: auth(teacher),
    })
  )
  await json(
    await request.patch(`/api/submissions/${submissions[0].id}/grade`, {
      headers: auth(teacher),
      data: { returned: true, feedback: '请补充应用场景', score: 0 },
    })
  )
  await login(page)
  const row = page.locator('.row').filter({ hasText: question.title }).first()
  await expect(row.getByText('待重做', { exact: true })).toBeVisible()
  await row.getByRole('button', { name: '去重做' }).click()
  await expect(page.locator('.detail h3')).toHaveText(question.title)
  await page.getByLabel('你的作业答案').fill('保留这份问答草稿')
  await page
    .locator('.filters')
    .getByRole('button', { name: /待重做/ })
    .click()
  await expect(page.locator('.list .item')).toHaveCount(1)
  await desktopTab(page, '知识库').click()
  await desktopTab(page, '作业中心').click()
  await expect(page.getByLabel('你的作业答案')).toHaveValue('保留这份问答草稿')
})

test('教师首页直达指定提交的批阅弹窗', async ({ page, request }) => {
  // 再次提交，恢复为待批阅状态。
  await json(
    await request.post(`/api/assignments/${question.id}/submit`, {
      headers: auth(student),
      data: { content: '栈用于撤销，队列用于排队。' },
    })
  )
  await login(page, teacher)
  await page.locator('.pending-row').filter({ hasText: question.title }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('dialog')).toContainText('界面测试学生')
  await expect(page.getByRole('dialog')).toContainText(question.title)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page
    .locator('#submission-list')
    .getByRole('button', { name: '批阅', exact: true })
    .first()
    .click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.goto('/#/home')
  await expect(page.locator('.teacher-hello')).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => document.body.style.overflow))
    .toBe('')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('手机导航、设置入口、弹窗焦点与各页面不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page)
  const nav = page.getByRole('navigation', { name: '移动端导航' })
  await expect(nav).toBeVisible()
  for (const label of ['首页', '作业中心', '学习助手', '知识库', '我的']) {
    await nav.getByRole('button', { name: label, exact: true }).click()
    await expect(page.locator('.view')).toBeVisible()
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)
      )
      .toBeTruthy()
  }
  const settings = page
    .getByRole('button', { name: '模型设置', exact: true })
    .first()
  await settings.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab')
    expect(
      await page.evaluate(
        () => !!document.activeElement.closest('[role="dialog"]')
      )
    ).toBeTruthy()
  }
  await page.keyboard.press('Escape')
  await expect(settings).toBeFocused()
})

test('聊天网络失败后可重试，引用可直达知识点', async ({ page }) => {
  await login(page, student, 'assistant')
  await page.route('**/api/chat', (route) => route.abort('failed'))
  await page.getByLabel('你的问题', { exact: true }).fill('链表如何插入？')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByRole('button', { name: '重新生成' })).toBeVisible()
  await page.unroute('**/api/chat')
  await page.route('**/api/chat', (route) =>
    route.fulfill({
      contentType: 'text/event-stream',
      body: 'data: {"token":"先想一想，应该保存哪个指针？"}\n\ndata: {"references":[{"kp_id":"ds-01-02","title":"单链表插入与删除"}]}\n\ndata: {"done":true}\n\n',
    })
  )
  await page.getByRole('button', { name: '重新生成' }).click()
  await expect(page.locator('.message.assistant')).toContainText('先想一想')
  await page.locator('.ref').click()
  await expect(page.locator('.item-card.expanded')).toContainText('插入')
})

test('中文输入法确认不发送，生成可以停止并恢复发送按钮', async ({ page }) => {
  await login(page, student, 'assistant')
  let requests = 0
  await page.route('**/api/chat', async (route) => {
    requests++
    await new Promise((resolve) => setTimeout(resolve, 2000))
    try {
      await route.fulfill({
        contentType: 'text/event-stream',
        body: 'data: {"done":true}\n\n',
      })
    } catch {}
  })
  const input = page.getByLabel('你的问题', { exact: true })
  await input.fill('输入法测试')
  await input.dispatchEvent('keydown', { key: 'Enter', isComposing: true })
  expect(requests).toBe(0)
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await expect(page.getByRole('button', { name: '停止生成' })).toBeVisible()
  await page.getByRole('button', { name: '停止生成' }).click()
  await expect(page.locator('.stream-error')).toContainText('已停止生成')
  await expect(
    page.getByRole('button', { name: '发送', exact: true })
  ).toBeVisible()
})

test('加载失败显示重试，恢复后正常显示数据', async ({ page }) => {
  await page.route('**/api/classes', (route) =>
    route.fulfill({ status: 503, json: { detail: '临时服务故障' } })
  )
  await login(page)
  await expect(page.locator('.async-error')).toContainText('临时服务故障')
  await page.unroute('**/api/classes')
  await page.getByRole('button', { name: '重新加载' }).click()
  await expect(page.locator('.hello')).toBeVisible()
})

test('教师登录过期后换学生登录回到学生首页', async ({ page }) => {
  await login(page, teacher, 'workspace')
  await expect(page.locator('.teacher-panel')).toBeVisible()
  await page.evaluate(() => window.dispatchEvent(new Event('auth-expired')))
  await page.getByLabel('用户名', { exact: true }).fill(student.username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.locator('.hello')).toBeVisible()
  await expect(page.locator('.teacher-panel')).toHaveCount(0)
  await expect(desktopTab(page, '作业中心')).toBeVisible()
})
