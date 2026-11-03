import hljs from 'highlight.js/lib/core'
import cpp from 'highlight.js/lib/languages/cpp'
import plaintext from 'highlight.js/lib/languages/plaintext'
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c', cpp)
hljs.registerLanguage('plaintext', plaintext)
export default hljs
