import { createApp } from 'vue'
import 'highlight.js/styles/github.css'
import './style.css'
import App from './App.vue'
import { dialog } from './composables/dialog.js'

createApp(App).directive('dialog', dialog).mount('#app')
