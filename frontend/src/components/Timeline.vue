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
const label = (m: (typeof marks.value)[number]) => `${m.clock} ${m.headline?.[profile.lang] ?? ''}`
// Keep the label inside the bar: left-align near the start, right-align near the end.
const edge = (e: number) =>
  e / total.value < 0.15 ? 'left-0' : e / total.value > 0.85 ? 'right-0' : 'left-1/2 -translate-x-1/2'
const teamColor = (side?: string | null) =>
  side === 'home' ? match.meta?.home.primary_color : side === 'away' ? match.meta?.away.primary_color : '#fff'
</script>

<template>
  <div
    class="relative mx-1 mb-1.5 mt-4 h-2 rounded bg-raised"
    role="progressbar"
    :aria-valuenow="Math.round(match.elapsed / 60)"
    aria-valuemin="0"
    :aria-valuemax="Math.round(total / 60)"
  >
    <div class="absolute inset-y-0 left-0 rounded bg-primary transition-[width] duration-500 ease-linear" :style="{ width: pct(match.elapsed) }" />
    <div class="absolute -inset-y-[3px] w-0.5 bg-muted" :style="{ left: pct(45 * 60) }" />
    <!-- The label is plain CSS (group-hover / group-focus), so a re-render on every match event cannot drop it. -->
    <span
      v-for="m in marks"
      :key="m.id"
      class="group absolute -top-5 z-10 grid -translate-x-1/2 cursor-default place-items-center p-1.5 outline-offset-0"
      :style="{ left: pct(m.elapsed) }"
      :aria-label="label(m)"
      role="img"
      tabindex="0"
    >
      <!-- goal: team-coloured disc; red card: red card shape; penalty: warning triangle -->
      <span
        v-if="m.type === 'goal'"
        class="size-3 rounded-full border-2 border-panel ring-1 ring-muted"
        :style="{ background: teamColor(m.team) }"
      />
      <span v-else-if="m.type === 'red_card'" class="h-3.5 w-2.5 rounded-[2px] bg-danger" />
      <i v-else class="pi pi-exclamation-triangle text-xs text-warn" aria-hidden="true" />
      <span
        class="pointer-events-none absolute bottom-full mb-1 hidden w-max max-w-64 rounded-md border border-line bg-ink px-2 py-1 text-left text-xs font-semibold text-on-ink group-hover:block group-focus:block"
        :class="edge(m.elapsed)"
        aria-hidden="true"
      >
        {{ label(m) }}
      </span>
    </span>
  </div>
</template>
