<script setup lang="ts">
import { computed } from 'vue'
import { useLayerEvents } from './useLayerEvents'

const { events, project } = useLayerEvents(['shot'])

const COLORS: Record<string, string> = { goal: '#f2d37a', saved: '#ffffff', blocked: '#ff8a73', off_target: '#d8d2c4' }

const shots = computed(() =>
  events.value.map((e) => {
    const d = e.data as Record<string, any>
    const p = project(e, e.location!)
    return {
      id: e.id,
      x: p.x,
      y: p.y,
      r: 0.8 + d.xg * 4,
      color: COLORS[d.outcome] ?? '#fff',
      goal: d.outcome === 'goal',
      title: `${e.clock.display} ${e.player?.name ?? ''} · xG ${d.xg.toFixed(2)} · ${d.speed_kmh} km/h · ${d.outcome}`,
    }
  }),
)
</script>

<template>
  <g class="shot-map">
    <circle
      v-for="s in shots"
      :key="s.id"
      :cx="s.x"
      :cy="s.y"
      :r="s.r"
      :fill="s.goal ? s.color : 'none'"
      :stroke="s.color"
      stroke-width="0.4"
      fill-opacity="0.85"
    >
      <title>{{ s.title }}</title>
    </circle>
  </g>
</template>
