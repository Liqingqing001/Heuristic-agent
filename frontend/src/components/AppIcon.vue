<script setup>
defineProps({
  name: { type: String, default: 'book' },
  size: { type: [Number, String], default: 20 },
})
const paths = {
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  workspace:
    'M3 21V5h8v16M11 9h10v12M6 8h2M6 12h2M6 16h2M15 12h2M15 16h2M1 21h22',
  homework: 'M9 5H5v16h14V5h-4M9 3h6v4H9ZM8 12h8M8 16h5',
  assistant:
    'm12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6ZM20 2v4M18 4h4',
  book: 'M12 5C8 2 3 3 2 4v16c4-2 7-1 10 1m0-16c4-3 9-2 10-1v16c-4-2-7-1-10 1ZM12 5v16',
  profile: 'M20 21a8 8 0 0 0-16 0M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  settings:
    'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 9l-1 3 1 3 3 1 1 3 4 2 4-2 1-3 3-1 1-3-1-3-3-1-1-3-4-2-4 2-1 3Z',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  check: 'm5 12 4 4L19 6',
  code: 'm8 5-7 7 7 7m8-14 7 7-7 7m-3-16-2 18',
  chat: 'M21 11a9 9 0 0 1-9 9H4l-3 2 2-6A9 9 0 1 1 21 11ZM7 10h10M7 14h6',
  chart: 'M4 3v18h17M8 16v-5m5 5V7m5 9V4',
  bug: 'M8 7h8v10a4 4 0 0 1-8 0ZM9 7V5a3 3 0 0 1 6 0v2M3 9l5 2m8 0 5-2M3 16h5m8 0h5M5 22l3-3m8 0 3 3M12 8v12',
  light: 'M9 18h6m-6 3h6M8 14a7 7 0 1 1 8 0l-1 2H9Z',
  target: 'M21 12a9 9 0 1 1-9-9m9 0-9 9m4-9h5v5M16 12a4 4 0 1 1-4-4',
}
</script>
<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name] || paths.book" />
  </svg>
</template>
