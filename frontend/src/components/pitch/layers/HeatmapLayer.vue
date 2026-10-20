<script setup lang="ts">
import { computed } from 'vue'
import { useLayerEvents } from './useLayerEvents'

const CELL = 5
const COLS = 21
const ROWS = 14

const { events, project } = useLayerEvents(['pass', 'carry', 'shot', 'tackle', 'interception', 'pressure'])

const cells = computed(() => {
  const grid = new Array<number>(COLS * ROWS).fill(0)
  for (const e of events.value) {
    const p = project(e, e.location!)
    const c = Math.min(COLS - 1, Math.floor(p.x / CELL))
    const r = Math.min(ROWS - 1, Math.floor(p.y / (68 / ROWS)))
    grid[r * COLS + c]++
  }
  const max = Math.max(1, ...grid)
  return grid
    .map((n, i) => ({ i, n, x: (i % COLS) * CELL, y: Math.floor(i / COLS) * (68 / ROWS), o: (n / max) * 0.8 }))
    .filter((c) => c.n > 0)
})
</script>

<template>
  <g class="heatmap">
    <rect
      v-for="c in cells"
      :key="c.i"
      :x="c.x"
      :y="c.y"
      :width="CELL"
      :height="68 / ROWS"
      fill="#f97316"
      :fill-opacity="c.o"
    />
  </g>
</template>
