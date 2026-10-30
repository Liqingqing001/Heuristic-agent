<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { cpp } from '@codemirror/lang-cpp'
import { oneDark } from '@codemirror/theme-one-dark'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const host = ref(null)
let view = null

onMounted(() => {
  view = new EditorView({
    doc: props.modelValue || '',
    extensions: [
      basicSetup,
      cpp(),
      oneDark,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          emit('update:modelValue', update.state.doc.toString())
        }
      }),
      EditorView.theme({
        '&': { fontSize: '13px', height: '280px' },
        '.cm-scroller': { fontFamily: 'Consolas, Menlo, monospace' },
      }),
    ],
    parent: host.value,
  })
})

watch(
  () => props.modelValue,
  (value) => {
    if (!view) return
    const current = view.state.doc.toString()
    if (value !== current) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value || '' },
      })
    }
  }
)

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})
</script>

<template>
  <div ref="host" class="code-editor"></div>
</template>

<style scoped>
.code-editor {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.code-editor :deep(.cm-editor) {
  outline: none;
}
</style>
