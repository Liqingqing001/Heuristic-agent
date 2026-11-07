import { createApp } from 'vue'
import 'highlight.js/styles/atom-one-dark.css'
import './style.css'
import App from './App.vue'
import { dialog } from './composables/dialog.js'

createApp(App).directive('dialog', dialog).mount('#app')
