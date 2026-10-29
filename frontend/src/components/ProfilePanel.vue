<script setup>
import { computed, onMounted, ref } from 'vue'
import { changePassword, getProfile, updateProfile } from '../api.js'
import { setUser, state } from '../session.js'

const profile = ref(null)
const form = ref({})
const active = ref('basic')
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')

const password = ref({ old: '', next: '', confirm: '' })
const passwordMessage = ref('')
const passwordError = ref('')
const passwordSaving = ref(false)

const avatarText = computed(() => {
  const name = form.value.real_name || form.value.display_name || profile.value?.username || '?'
  return name.trim().slice(0, 1).toUpperCase()
})

const roleLabel = computed(() => (profile.value?.role === 'teacher' ? '教师' : '学生'))

async function load() {
  loading.value = true
  const data = await getProfile()
  if (data) {
    profile.value = data
    form.value = { ...data }
  }
  loading.value = false
}

async function save() {
  error.value = ''
  message.value = ''
  saving.value = true
  try {
    const updated = await updateProfile({
      real_name: form.value.real_name || '',
      display_name: form.value.display_name || '',
      school: form.value.school || '',
      department: form.value.department || '',
      major: form.value.major || '',
      gender: form.value.gender || '',
      enrollment_year: form.value.enrollment_year || '',
      bio: form.value.bio || '',
    })
    profile.value = updated
    form.value = { ...updated }
    if (state.user) {
      setUser({ ...state.user, display_name: updated.display_name, role: updated.role })
    }
    message.value = '已保存'
  } catch (e) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function submitPassword() {
  passwordError.value = ''
  passwordMessage.value = ''
  if (password.value.next !== password.value.confirm) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  passwordSaving.value = true
  try {
    await changePassword(password.value.old, password.value.next)
    passwordMessage.value = '密码已修改，下次请用新密码登录'
    password.value = { old: '', next: '', confirm: '' }
  } catch (e) {
    passwordError.value = e.message || '修改失败'
  } finally {
    passwordSaving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading">加载中…</div>

  <div v-else class="profile">
    <aside class="side">
      <div class="avatar">{{ avatarText }}</div>
      <h2>{{ form.real_name || form.display_name || profile?.username }}</h2>
      <p class="role">{{ roleLabel }}<span v-if="profile?.username"> · {{ profile.username }}</span></p>

      <div class="menu">
        <div class="menu-title">账号管理</div>
        <button :class="{ active: active === 'basic' }" @click="active = 'basic'">
          <span>👤 基本信息</span>
          <span class="dot ok"></span>
        </button>
        <button :class="{ active: active === 'security' }" @click="active = 'security'">
          <span>🔒 安全设置</span>
          <span class="dot"></span>
        </button>
      </div>
    </aside>

    <section class="main">
      <template v-if="active === 'basic'">
        <h3>基本信息</h3>
        <div class="grid">
          <label>
            <span>姓名</span>
            <input v-model="form.real_name" placeholder="你的真实姓名" />
          </label>
          <label>
            <span>昵称</span>
            <input v-model="form.display_name" placeholder="显示在班级里的名字" />
          </label>
          <label>
            <span>账号</span>
            <input :value="profile?.username" disabled />
          </label>
          <label>
            <span>身份</span>
            <input :value="roleLabel" disabled />
          </label>
          <label>
            <span>学校 / 单位</span>
            <input v-model="form.school" placeholder="例如：深圳技术大学" />
          </label>
          <label>
            <span>院系 / 部门</span>
            <input v-model="form.department" placeholder="例如：大数据与互联网学院" />
          </label>
          <label>
            <span>专业</span>
            <input v-model="form.major" placeholder="例如：数据科学与大数据技术" />
          </label>
          <label>
            <span>性别</span>
            <select v-model="form.gender">
              <option value="">未填写</option>
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="其他">其他</option>
            </select>
          </label>
          <label>
            <span>入学年份</span>
            <input v-model="form.enrollment_year" placeholder="例如：2024" />
          </label>
        </div>

        <label class="full">
          <span>简介</span>
          <textarea v-model="form.bio" placeholder="一句话介绍自己，最多 300 字"></textarea>
        </label>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="message" class="ok">{{ message }}</p>

        <div class="actions">
          <button class="primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </template>

      <template v-else>
        <h3>安全设置</h3>
        <p class="tip">修改密码后，其他设备上的登录不会被强制退出；如果怀疑账号泄露，请同时修改。</p>

        <label class="full">
          <span>原密码</span>
          <input v-model="password.old" type="password" autocomplete="current-password" />
        </label>
        <label class="full">
          <span>新密码（至少 6 位）</span>
          <input v-model="password.next" type="password" autocomplete="new-password" />
        </label>
        <label class="full">
          <span>确认新密码</span>
          <input v-model="password.confirm" type="password" autocomplete="new-password" />
        </label>

        <p v-if="passwordError" class="error">{{ passwordError }}</p>
        <p v-if="passwordMessage" class="ok">{{ passwordMessage }}</p>

        <div class="actions">
          <button class="primary" :disabled="passwordSaving" @click="submitPassword">
            {{ passwordSaving ? '提交中…' : '修改密码' }}
          </button>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.loading {
  padding: 60px;
  text-align: center;
  color: #94a3b8;
}

.profile {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.side {
  width: 260px;
  flex-shrink: 0;
  background: white;
  border: 1px solid #e8eef6;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
  padding: 24px 0 18px;
  text-align: center;
}

.avatar {
  width: 96px;
  height: 96px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fca5a5, #fdba74);
  color: white;
  font-size: 38px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.side h2 {
  margin: 0;
  font-size: 20px;
  color: #1e293b;
}

.role {
  margin: 6px 0 20px;
  font-size: 13px;
  color: #64748b;
}

.menu {
  text-align: left;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}

.menu-title {
  font-size: 14px;
  color: #334155;
  padding: 6px 20px 10px;
}

.menu button {
  width: 100%;
  border: none;
  background: transparent;
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  border-left: 3px solid transparent;
}

.menu button:hover {
  background: #f8fafc;
}

.menu button.active {
  background: #eff6ff;
  border-left-color: #3b82f6;
  color: #1d4ed8;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e2e8f0;
}

.dot.ok {
  background: #22c55e;
}

.main {
  flex: 1;
  min-width: 0;
  padding: 4px 8px;
}

.main h3 {
  margin: 0 0 18px;
  font-size: 16px;
  color: #1e293b;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 24px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}

label.full {
  margin-top: 16px;
}

input,
select,
textarea {
  padding: 9px 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  font-size: 13px;
  color: #1e293b;
  background: white;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #3b82f6;
  outline: none;
}

input:disabled {
  background: #f8fafc;
  color: #94a3b8;
}

textarea {
  min-height: 90px;
  resize: vertical;
}

.tip {
  font-size: 12px;
  color: #94a3b8;
  margin: 0 0 12px;
  line-height: 1.7;
}

.actions {
  margin-top: 22px;
}

.primary {
  padding: 9px 22px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 13px;
  cursor: pointer;
}

.primary:hover:not(:disabled) {
  background: #2563eb;
}

.primary:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.error {
  color: #ef4444;
  font-size: 12px;
  margin: 12px 0 0;
}

.ok {
  color: #15803d;
  font-size: 12px;
  margin: 12px 0 0;
}

@media (max-width: 860px) {
  .profile {
    flex-direction: column;
  }

  .side {
    width: 100%;
  }

  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
