<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMatch } from '@/stores/match'

const { t } = useI18n()
const match = useMatch()

const W = 300
const H = 64
const total = computed(() => {
  const s = match.meta?.stoppage_minutes ?? {}
  return 90 * 60 + ((s['1'] ?? 2) + (s['2'] ?? 4)) * 60
})
const x = (elapsed: number) => (elapsed / total.value) * W
const y = (v: number) => H / 2 - v * (H / 2 - 4)

const path = computed(() => {
  const pts = match.momentumHistory
  if (pts.length < 2) return ''
  return `M ${x(pts[0].elapsed)} ${H / 2} ` + pts.map((p) => `L ${x(p.elapsed).toFixed(1)} ${y(p.value).toFixed(1)}`).join(' ') + ` L ${x(pts[pts.length - 1].elapsed)} ${H / 2} Z`
})
const goals = computed(() => match.moments.filter((m) => m.type === 'goal'))
const colorOf = (side?: string | null) => (side === 'home' ? match.meta?.home.primary_color : match.meta?.away.primary_color)
</script>

<template>
  <section class="panel">
    <h2>{{ t('momentum.title') }}</h2>
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" role="img" :aria-label="t('momentum.title')">
      <defs>
        <clipPath id="top"><rect x="0" y="0" :width="W" :height="H / 2" /></clipPath>
        <clipPath id="bottom"><rect x="0" :y="H / 2" :width="W" :height="H / 2" /></clipPath>
      </defs>
      <line x1="0" :x2="W" :y1="H / 2" :y2="H / 2" stroke="var(--line)" />
      <line :x1="x(45 * 60)" :x2="x(45 * 60)" y1="0" :y2="H" stroke="var(--line)" stroke-dasharray="2 2" />
      <path :d="path" :fill="colorOf('home')" fill-opacity="0.75" clip-path="url(#top)" />
      <path :d="path" :fill="colorOf('away')" fill-opacity="0.75" clip-path="url(#bottom)" />
      <g v-for="g in goals" :key="g.id">
        <line :x1="x(g.elapsed)" :x2="x(g.elapsed)" y1="0" :y2="H" stroke="#fff" stroke-width="1" />
        <text :x="x(g.elapsed)" :y="g.team === 'home' ? 9 : H - 2" font-size="9" text-anchor="middle">⚽</text>
      </g>
    </svg>
    <div class="legend muted">
      <span>{{ match.meta?.home.short_name }} ▲</span>
      <span>▼ {{ match.meta?.away.short_name }}</span>
    </div>
  </section>
</template>

<style scoped>
.chart {
  width: 100%;
  height: 80px;
  display: block;
}
.legend {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
}
</style>
