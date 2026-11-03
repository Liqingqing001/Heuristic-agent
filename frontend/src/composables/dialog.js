// 焦点限制、Esc 关闭和关闭后的焦点恢复，供所有模态框复用。
const stack = []
export const dialog = {
  mounted(el, binding) {
    const previous = document.activeElement
    el.setAttribute('role', 'dialog')
    el.setAttribute('aria-modal', 'true')
    el.setAttribute(
      'aria-label',
      el.querySelector('h3')?.textContent || '对话框'
    )
    el.tabIndex = -1
    const focusable = () =>
      [
        ...el.querySelectorAll(
          'button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),a[href],[tabindex="0"]'
        ),
      ].filter((item) => item.getClientRects().length)
    const entry = { el }
    stack.push(entry)
    const keydown = (e) => {
      if (stack.at(-1) !== entry) return
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        binding.value?.()
      }
      if (e.key === 'Tab') {
        const nodes = focusable()
        const first = nodes[0] || el
        const last = nodes.at(-1) || el
        if (
          e.shiftKey &&
          (document.activeElement === first || document.activeElement === el)
        ) {
          e.preventDefault()
          last.focus()
        } else if (
          !e.shiftKey &&
          (document.activeElement === last ||
            !el.contains(document.activeElement))
        ) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    const focusin = (e) => {
      if (stack.at(-1) === entry && !el.contains(e.target))
        (focusable()[0] || el).focus()
    }
    document.addEventListener('keydown', keydown)
    document.addEventListener('focusin', focusin)
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    requestAnimationFrame(() => {
      if (el.isConnected) (focusable()[0] || el).focus()
    })
    el._disposeDialog = () => {
      document.removeEventListener('keydown', keydown)
      document.removeEventListener('focusin', focusin)
      const index = stack.indexOf(entry)
      if (index !== -1) stack.splice(index, 1)
      document.body.style.overflow = oldOverflow
      if (previous?.isConnected) previous.focus()
    }
  },
  beforeUnmount(el) {
    el._disposeDialog?.()
  },
}
