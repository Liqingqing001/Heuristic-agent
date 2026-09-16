<script setup>
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { streamAnalyze } from '../api.js'

const code = ref('')
const language = ref('cpp')
const question = ref('')
const result = ref('')
const loading = ref(false)
const resultBox = ref(null)

const renderMarkdown = (text) => marked.parse(text)

function highlight() {
  if (!resultBox.value) return
  resultBox.value.querySelectorAll('pre code').forEach((b) => {
    try {
      hljs.highlightElement(b)
    } catch (e) {
      /* 忽略 */
    }
  })
}

async function submit() {
  const c = code.value.trim()
  if (!c || loading.value) return
  result.value = ''
  loading.value = true

  await streamAnalyze(
    {
      code: c,
      language: language.value,
      question: question.value.trim() || null,
    },
    (token) => {
      result.value += token
    },
    (err) => {
      result.value += `\n\n⚠️ 出错：${err}`
    }
  )

  loading.value = false
  nextTick(highlight)
}
</script>

<template>
  <div>
    <div class="code-form">
      <textarea v-model="code" placeholder="粘贴你的 C/C++ 代码…"></textarea>
      <div class="row">
        <select v-model="language">
          <option value="cpp">C++</option>
          <option value="c">C</option>
        </select>
        <input v-model="question" placeholder="（可选）描述你遇到的问题" style="flex: 1;" />
        <button :disabled="loading || !code.trim()" @click="submit">
          {{ loading ? '诊断中…' : '开始剖析' }}
        </button>
      </div>
    </div>

    <div v-if="result" ref="resultBox" class="result-box" v-html="renderMarkdown(result)"></div>
    <div v-else class="empty-hint">
      提交一段代码，助教会先诊断逻辑问题，再用提问引导你自己修复——绝不直接给完整代码。
    </div>
  </div>
</template>
