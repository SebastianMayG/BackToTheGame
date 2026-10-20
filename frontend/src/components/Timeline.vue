<script setup lang="ts">
import { computed } from 'vue'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

const match = useMatch()
const profile = useProfile()
const MARKS = new Set(['goal', 'red_card', 'penalty_awarded'])

const total = computed(() => {
  const s = match.meta?.stoppage_minutes ?? {}
  return 90 * 60 + ((s['1'] ?? 2) + (s['2'] ?? 4)) * 60
})
const pct = (e: number) => `${Math.min(100, (e / total.value) * 100)}%`
const marks = computed(() => match.moments.filter((m) => MARKS.has(m.type)))
const icon = (type: string) => ({ goal: '⚽', red_card: '🟥', penalty_awarded: '⚠️' })[type] ?? '•'
</script>

<template>
  <div class="timeline" role="progressbar" :aria-valuenow="Math.round(match.elapsed / 60)" aria-valuemin="0" :aria-valuemax="Math.round(total / 60)">
    <div class="played" :style="{ width: pct(match.elapsed) }" />
    <div class="half" :style="{ left: pct(45 * 60) }" />
    <span
      v-for="m in marks"
      :key="m.id"
      class="mark"
      :class="m.team ?? ''"
      :style="{ left: pct(m.elapsed) }"
      :title="`${m.clock} ${m.headline?.[profile.lang] ?? ''}`"
    >
      {{ icon(m.type) }}
    </span>
  </div>
</template>

<style scoped>
.timeline {
  position: relative;
  height: 8px;
  background: var(--panel-2);
  border-radius: 4px;
  margin: 14px 4px 6px;
}
.played {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--accent);
  border-radius: 4px;
  transition: width 0.5s linear;
}
.half {
  position: absolute;
  top: -3px;
  bottom: -3px;
  width: 2px;
  background: var(--muted);
}
.mark {
  position: absolute;
  top: -14px;
  transform: translateX(-50%);
  font-size: 0.8rem;
}
</style>
