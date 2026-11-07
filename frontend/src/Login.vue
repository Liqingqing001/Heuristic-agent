<script setup>
import { ref } from 'vue'
import { apiLogin, apiRegister } from './api.js'
import AppIcon from './components/AppIcon.vue'
const emit = defineEmits(['success'])
const mode = ref('login'),
  username = ref(''),
  password = ref(''),
  displayName = ref(''),
  role = ref('student'),
  error = ref(''),
  loading = ref(false),
  showPassword = ref(false)
async function submit() {
  if (loading.value) return
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  if (mode.value === 'register' && password.value.length < 6) {
    error.value = '密码至少需要 6 位'
    return
  }
  loading.value = true
  try {
    if (mode.value === 'login')
      await apiLogin(username.value.trim(), password.value)
    else
      await apiRegister(
        username.value.trim(),
        password.value,
        role.value,
        displayName.value.trim()
      )
    emit('success')
  } catch (e) {
    error.value = e.message || '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
  password.value = ''
}
</script>
<template>
  <div class="login-page">
    <section class="login-story">
      <div class="brand">
        <span class="brand-mark">智</span><strong>数据结构智育助教</strong>
      </div>
      <div class="story-content">
        <span class="story-tag">你的数据结构学习伙伴</span>
        <h1>答案之外，<br />还有更好的<span>思考方式。</span></h1>
        <p>把复杂的问题拆小一点。<br />从理解一个指针，到掌握一种解法。</p>
        <div class="story-features">
          <span><AppIcon name="chat" :size="18" />启发式提问</span
          ><span><AppIcon name="code" :size="18" />代码诊断</span
          ><span><AppIcon name="chart" :size="18" />学习反馈</span>
        </div>
      </div>
      <small>引导思考 · 理解原理 · 学会迁移</small>
    </section>
    <main class="login-main">
      <div class="login-card">
        <span class="eyebrow">{{
          mode === 'login' ? 'WELCOME BACK' : 'START YOUR JOURNEY'
        }}</span>
        <h2>{{ mode === 'login' ? '欢迎回来' : '开启你的学习旅程' }}</h2>
        <p class="sub">
          {{
            mode === 'login'
              ? '登录账户，继续上一次的探索。'
              : '选择身份，创建属于你的工作空间。'
          }}
        </p>
        <form @submit.prevent="submit" :aria-busy="loading">
          <fieldset v-if="mode === 'register'" class="role-picker">
            <legend>你的身份</legend>
            <label :class="{ active: role === 'student' }"
              ><input
                v-model="role"
                type="radio"
                value="student"
                name="role"
              /><AppIcon name="book" /><strong>我是学生</strong></label
            ><label :class="{ active: role === 'teacher' }"
              ><input
                v-model="role"
                type="radio"
                value="teacher"
                name="role"
              /><AppIcon name="workspace" /><strong>我是教师</strong></label
            >
          </fieldset>
          <label class="field" for="username"
            >用户名<input
              id="username"
              v-model="username"
              autocomplete="username"
              placeholder="输入你的用户名"
              required
          /></label>
          <label class="field" for="password"
            >密码<span class="password-field"
              ><input
                id="password"
                aria-label="密码"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                :autocomplete="
                  mode === 'login' ? 'current-password' : 'new-password'
                "
                :placeholder="
                  mode === 'login' ? '输入你的密码' : '设置密码，至少 6 位'
                "
                :minlength="mode === 'register' ? 6 : undefined"
                required
              /><button
                type="button"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button></span
            ></label
          >
          <label v-if="mode === 'register'" class="field" for="display-name"
            >姓名 / 昵称 <span class="muted">（可选）</span
            ><input
              id="display-name"
              v-model="displayName"
              autocomplete="name"
              placeholder="你希望被怎样称呼"
          /></label>
          <p v-if="error" class="login-error" role="alert">{{ error }}</p>
          <button class="submit-button" :disabled="loading" type="submit">
            {{ loading ? '正在连接…' : mode === 'login' ? '登录' : '创建账户' }}
            <AppIcon v-if="!loading" name="arrow" :size="18" />
          </button>
        </form>
        <p class="switch">
          {{ mode === 'login' ? '还没有账户？' : '已经有账户？'
          }}<button @click="switchMode">
            {{ mode === 'login' ? '立即注册' : '返回登录' }}
          </button>
        </p>
        <div class="login-note">
          <AppIcon name="light" :size="17" />我们提供启发，让你自己找到答案。
        </div>
      </div>
      <footer>数据结构智育助教 · 数据结构与算法学习空间</footer>
    </main>
  </div>
</template>
<style scoped>
.login-page {
  display: grid;
  grid-template-columns: 46% 54%;
  min-height: 100dvh;
  background: #fff;
}
.login-story {
  display: flex;
  flex-direction: column;
  padding: 40px 52px;
  background: #edf2fc;
  position: relative;
  overflow: hidden;
}
.login-story::after {
  content: '';
  width: 420px;
  height: 420px;
  border: 70px solid #3264d806;
  border-radius: 50%;
  position: absolute;
  bottom: -200px;
  right: -150px;
  pointer-events: none;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 19px;
}
.story-content {
  margin: auto 0;
  padding: 60px 0;
}
.story-tag {
  font-size: 12px;
  letter-spacing: 3px;
  color: var(--primary);
}
h1 {
  font-size: clamp(30px, 3.5vw, 52px);
  line-height: 1.45;
  font-weight: 650;
  letter-spacing: -1.5px;
  margin: 22px 0;
}
h1 span {
  color: var(--primary);
  display: block;
}
.story-content p {
  font-size: 14px;
  line-height: 2;
  color: var(--muted);
}
.story-features {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-top: 40px;
}
.story-features span {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #526582;
}
.login-story > small {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 2px;
}
.login-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  position: relative;
}
.login-card {
  width: 100%;
  max-width: 360px;
}
h2 {
  font-size: 29px;
  letter-spacing: -0.7px;
  margin: 10px 0;
}
.sub {
  color: var(--muted);
  font-size: 13px;
  margin: 0 0 30px;
}
.field {
  display: block;
  font-size: 13px;
  font-weight: 550;
  margin-top: 18px;
}
.field input {
  display: block;
  width: 100%;
  border: 1px solid #dbe2ed;
  border-radius: 9px;
  background: #fcfdff;
  padding: 12px 14px;
  font-size: 14px;
  margin-top: 8px;
  font-weight: 400;
  outline: none;
}
.password-field {
  display: flex;
  align-items: center;
  position: relative;
}
.password-field input {
  padding-right: 58px;
}
.password-field button {
  position: absolute;
  right: 12px;
  top: 21px;
  background: none;
  border: 0;
  color: var(--muted);
  font-size: 12px;
}
.submit-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  width: 100%;
  background: var(--primary);
  color: white;
  border: 0;
  border-radius: 9px;
  padding: 13px;
  margin-top: 26px;
  font-size: 14px;
  font-weight: 550;
}
.submit-button:hover {
  background: var(--primary-dark);
}
.switch {
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  margin-top: 24px;
}
.switch button {
  background: none;
  border: 0;
  color: var(--primary);
  font-size: 13px;
  padding: 4px 6px;
}
.login-note {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--border);
  margin-top: 30px;
  padding-top: 22px;
  font-size: 12px;
  color: var(--muted);
}
footer {
  position: absolute;
  bottom: 24px;
  font-size: 11px;
  color: var(--muted);
}
.login-error {
  background: #fff3f2;
  border: 1px solid #f9d6d2;
  color: #af3933;
  border-radius: 8px;
  padding: 10px;
  font-size: 13px;
}
.role-picker {
  border: 0;
  padding: 0;
  display: flex;
  gap: 12px;
  margin: 0;
}
.role-picker legend {
  font-size: 13px;
  margin-bottom: 9px;
}
.role-picker label {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 13px 10px;
  border: 1px solid var(--border);
  border-radius: 9px;
  flex: 1;
  font-size: 12px;
  cursor: pointer;
}
.role-picker label.active {
  color: var(--primary);
  background: #f0f5ff;
  border-color: #b7caf7;
}
.role-picker input {
  accent-color: var(--primary);
  margin: 0;
}
@media (max-width: 760px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .login-story {
    padding: 24px;
  }
  .story-content {
    padding: 26px 0 8px;
  }
  .story-content h1 {
    font-size: 29px;
    margin: 14px 0;
  }
  .story-content h1 br {
    display: none;
  }
  .story-content h1 span {
    display: inline;
  }
  .story-content p,
  .story-features,
  .login-story > small {
    display: none;
  }
  .story-tag {
    font-size: 10px;
  }
  .login-main {
    padding: 32px 24px 70px;
  }
  .login-card {
    max-width: 420px;
  }
  h2 {
    font-size: 25px;
  }
  .login-main footer {
    bottom: 20px;
  }
  .sub {
    margin-bottom: 23px;
  }
  .field input {
    font-size: 16px;
  }
}
</style>
