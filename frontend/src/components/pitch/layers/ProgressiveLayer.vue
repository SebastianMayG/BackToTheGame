<script setup lang="ts">
import { computed } from 'vue'
import { useMatch } from '@/stores/match'
import { useLayerEvents } from './useLayerEvents'

const match = useMatch()
const { events, project } = useLayerEvents(['pass'])

const passes = computed(() =>
  events.value
    .filter((e) => {
      const d = e.data as Record<string, any>
      return d.outcome === 'complete' && d.progressive >= 10
    })
    .slice(-80)
    .map((e) => {
      const d = e.data as Record<string, any>
      const a = project(e, e.location!)
      const b = project(e, d.end_location)
      const club = e.team === 'home' ? match.meta?.home : match.meta?.away
      return { id: e.id, a, b, color: club?.primary_color ?? '#fff', title: `${e.clock.display} ${e.player?.name} → ${d.recipient?.name} (+${d.progressive} m)` }
    }),
)
</script>

<template>
  <g class="progressive">
    <line
      v-for="p in passes"
      :key="p.id"
      :x1="p.a.x"
      :y1="p.a.y"
      :x2="p.b.x"
      :y2="p.b.y"
      :stroke="p.color"
      stroke-width="0.45"
      stroke-opacity="0.9"
      marker-end="url(#arrow)"
    >
      <title>{{ p.title }}</title>
    </line>
  </g>
</template>
