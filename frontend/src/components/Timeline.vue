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
    <span
      v-for="m in marks"
      :key="m.id"
      v-tooltip.top="label(m)"
      class="absolute -top-4 grid -translate-x-1/2 place-items-center"
      :style="{ left: pct(m.elapsed) }"
      :aria-label="label(m)"
    >
      <!-- goal: team-coloured disc; red card: red card shape; penalty: warning triangle -->
      <span
        v-if="m.type === 'goal'"
        class="size-3 rounded-full border-2 border-white"
        :style="{ background: teamColor(m.team) }"
      />
      <span v-else-if="m.type === 'red_card'" class="h-3.5 w-2.5 rounded-[2px] bg-danger" />
      <i v-else class="pi pi-exclamation-triangle text-xs text-warn" aria-hidden="true" />
    </span>
  </div>
</template>
