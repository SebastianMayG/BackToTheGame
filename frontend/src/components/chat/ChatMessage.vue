<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CommentaryLine } from '@/api/types'

const props = defineProps<{ line: CommentaryLine }>()
const { t } = useI18n()

const icon = computed(() => ({ narrator: '🎙️', pundit: '🎓', system: '📣' })[props.line.speaker])
</script>

<template>
  <li class="msg" :class="[line.speaker, `lvl${line.level}`, line.emotion]">
    <span class="clock">{{ line.clock }}</span>
    <div class="body">
      <span class="who">
        <span aria-hidden="true">{{ icon }}</span>
        {{ t(`chat.${line.speaker}`) }}
        <span class="src" :class="line.source">{{ t(`chat.${line.source}`) }}</span>
      </span>
      <p>{{ line.text }}</p>
    </div>
  </li>
</template>

<style scoped>
.msg {
  display: grid;
  grid-template-columns: 74px 1fr;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  animation: slide-in 0.25s ease-out;
}
.clock {
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  font-size: 0.8rem;
  padding-top: 2px;
}
.who {
  font-size: 0.72rem;
  color: var(--muted);
  display: flex;
  gap: 6px;
  align-items: center;
}
.src {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 6px;
  font-size: 0.65rem;
}
.src.ai {
  border-color: var(--accent-2);
  color: var(--accent-2);
}
p {
  margin: 2px 0 0;
  line-height: 1.35;
}
.lvl3 p {
  color: var(--muted);
  font-size: 0.9rem;
}
.lvl1 {
  background: var(--panel-2);
}
.lvl1 p {
  font-weight: 700;
}
.lvl1.excited {
  border-left: 4px solid var(--accent);
}
.lvl1.disappointed {
  border-left: 4px solid var(--danger);
}
.pundit {
  background: color-mix(in srgb, var(--accent-2) 8%, transparent);
}
.pundit p {
  font-style: italic;
}
.system {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}
@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .msg {
    animation: none;
  }
}
</style>
