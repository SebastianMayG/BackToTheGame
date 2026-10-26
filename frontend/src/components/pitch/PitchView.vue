<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import { useView } from '@/stores/view'
import { teamShape, viewTransform } from '@/lib/pitch'
import type { Side } from '@/api/types'
import ShotMapLayer from './layers/ShotMapLayer.vue'
import HeatmapLayer from './layers/HeatmapLayer.vue'
import ProgressiveLayer from './layers/ProgressiveLayer.vue'

const match = useMatch()
const profile = useProfile()
const view = useView()

const toView = computed(() => viewTransform(view.viewSide, match.period))

const players = computed(() =>
  teamShape(match.lineups, match.ball, match.possession, match.period, match.carrierId).map((p) => ({
    ...p,
    ...toView.value({ x: p.x, y: p.y }),
  })),
)
const ball = computed(() => toView.value(match.ball))

const colors = computed(() => ({
  home: { fill: match.meta?.home.primary_color ?? '#c00', stroke: match.meta?.home.secondary_color ?? '#fff' },
  away: { fill: match.meta?.away.primary_color ?? '#00c', stroke: match.meta?.away.secondary_color ?? '#fff' },
}))

function dimmed(side: Side): boolean {
  return profile.mode === 'fan' && view.favSide !== null && side !== view.favSide
}

// Short-lived tags over the pitch: sprint and shot speeds.
interface Tag { x: number; y: number; text: string; kind: 'speed' | 'shot' }
const tag = ref<Tag | null>(null)
let tagTimer: number | undefined
watch(
  () => match.last,
  (ev) => {
    if (!ev || !ev.location) return
    const d = (ev.data ?? {}) as Record<string, any>
    let t: Tag | null = null
    if (ev.type === 'carry' && d.sprint && d.top_speed_kmh >= 30) {
      const p = toView.value(d.end_location)
      t = { ...p, text: `${d.top_speed_kmh.toFixed(1)} km/h`, kind: 'speed' }
    } else if (ev.type === 'shot') {
      const p = toView.value(ev.location)
      t = { ...p, text: `${d.speed_kmh.toFixed(0)} km/h · xG ${d.xg.toFixed(2)}`, kind: 'shot' }
    }
    if (t) {
      tag.value = t
      window.clearTimeout(tagTimer)
      tagTimer = window.setTimeout(() => (tag.value = null), 2600)
    }
  },
)

// Broadcast lower third for the biggest moments.
const LOWER_THIRD = new Set(['goal', 'red_card', 'penalty_awarded'])
const lowerThird = ref<{ clock: string; text: string } | null>(null)
let ltTimer: number | undefined
watch(
  () => match.moments.length,
  () => {
    const m = match.moments[match.moments.length - 1]
    if (!m || !LOWER_THIRD.has(m.type)) return
    lowerThird.value = { clock: m.clock, text: m.headline?.[profile.lang] ?? '' }
    window.clearTimeout(ltTimer)
    ltTimer = window.setTimeout(() => (lowerThird.value = null), 4500)
  },
)
onBeforeUnmount(() => {
  window.clearTimeout(tagTimer)
  window.clearTimeout(ltTimer)
})

const label = computed(() => {
  const m = match.meta
  if (!m) return ''
  return `${m.home.name} ${match.score.home} - ${match.score.away} ${m.away.name}, ${match.clock}`
})
</script>

<template>
  <div class="pitch-wrap">
    <svg class="pitch" viewBox="-4 -4 113 76" role="img" :aria-label="label">
      <defs>
        <pattern id="stripes" width="10.5" height="68" patternUnits="userSpaceOnUse">
          <rect width="5.25" height="68" fill="var(--grass-1)" />
          <rect x="5.25" width="5.25" height="68" fill="var(--grass-2)" />
        </pattern>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
        </marker>
      </defs>

      <!-- markings -->
      <rect x="-4" y="-4" width="113" height="76" fill="var(--grass-2)" />
      <rect x="0" y="0" width="105" height="68" fill="url(#stripes)" />
      <g fill="none" stroke="var(--pitch-line)" stroke-width="0.3">
        <rect x="0" y="0" width="105" height="68" />
        <line x1="52.5" y1="0" x2="52.5" y2="68" />
        <circle cx="52.5" cy="34" r="9.15" />
        <rect x="0" y="13.84" width="16.5" height="40.32" />
        <rect x="88.5" y="13.84" width="16.5" height="40.32" />
        <rect x="0" y="24.84" width="5.5" height="18.32" />
        <rect x="99.5" y="24.84" width="5.5" height="18.32" />
        <path d="M 16.5 26.69 A 9.15 9.15 0 0 1 16.5 41.31" />
        <path d="M 88.5 26.69 A 9.15 9.15 0 0 0 88.5 41.31" />
        <rect x="-1.5" y="30.34" width="1.5" height="7.32" />
        <rect x="105" y="30.34" width="1.5" height="7.32" />
      </g>
      <g fill="var(--pitch-line)">
        <circle cx="52.5" cy="34" r="0.4" />
        <circle cx="11" cy="34" r="0.4" />
        <circle cx="94" cy="34" r="0.4" />
      </g>

      <!-- analyst layers -->
      <HeatmapLayer v-if="view.layer === 'heatmap'" />
      <ShotMapLayer v-if="view.layer === 'shot_map'" />
      <ProgressiveLayer v-if="view.layer === 'progressive'" />

      <!-- players -->
      <g
        v-for="p in players"
        :key="p.player.id"
        class="player"
        :class="{ dim: dimmed(p.side), fav: p.player.id === profile.player }"
        :style="{ transform: `translate(${p.x}px, ${p.y}px)` }"
      >
        <circle v-if="p.player.id === profile.player" class="halo" r="3.2" />
        <circle r="1.7" :fill="colors[p.side].fill" :stroke="colors[p.side].stroke" stroke-width="0.35" />
        <text class="num" y="0.6" :fill="colors[p.side].stroke">{{ p.player.number }}</text>
        <text v-if="profile.names || p.onBall || p.player.id === profile.player" class="name" y="3.9">
          {{ p.player.name.split(' ').slice(-1)[0] }}
        </text>
      </g>

      <!-- ball -->
      <g class="ball" :style="{ transform: `translate(${ball.x}px, ${ball.y}px)` }">
        <circle r="0.9" fill="#fff" stroke="#111" stroke-width="0.2" />
      </g>

      <!-- speed / shot tags -->
      <g v-if="tag" class="tag" :transform="`translate(${Math.min(92, Math.max(8, tag.x))}, ${Math.max(5, tag.y - 4)})`">
        <rect x="-9" y="-2.6" width="18" height="3.6" rx="1" :class="tag.kind" />
        <text y="0.3">{{ tag.text }}</text>
      </g>
    </svg>

    <transition name="lt">
      <div v-if="lowerThird" class="lower-third" aria-hidden="true">
        <span class="clock">{{ lowerThird.clock }}</span>
        <span>{{ lowerThird.text }}</span>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.pitch-wrap {
  position: relative;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--line);
}
.pitch {
  display: block;
  width: 100%;
  height: auto;
}
.player,
.ball {
  transition: transform 0.55s ease-out;
}
.ball {
  transition-duration: 0.4s;
}
.player.dim {
  opacity: 0.55;
}
.num {
  font-size: 1.7px;
  font-weight: 800;
  text-anchor: middle;
  pointer-events: none;
}
.name {
  font-size: 1.9px;
  fill: #fff;
  text-anchor: middle;
  paint-order: stroke;
  stroke: rgba(0, 0, 0, 0.75);
  stroke-width: 0.5px;
  font-weight: 600;
}
.halo {
  fill: none;
  stroke: var(--gold-light);
  stroke-width: 0.5;
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    r: 3;
  }
  50% {
    opacity: 0.35;
    r: 3.8;
  }
}
.tag rect {
  fill: rgba(27, 31, 42, 0.85);
  stroke: var(--on-ink);
  stroke-width: 0.2;
}
.tag rect.shot {
  stroke: var(--gold-light);
}
.tag text {
  font-size: 2px;
  fill: var(--on-ink);
  text-anchor: middle;
  font-weight: 700;
}
.lower-third {
  position: absolute;
  left: 4%;
  right: 4%;
  bottom: 5%;
  display: flex;
  gap: 10px;
  align-items: center;
  background: var(--ink);
  color: var(--on-ink);
  border-left: 5px solid var(--gold-light);
  padding: 10px 14px;
  border-radius: 6px;
  font-weight: 700;
  font-size: clamp(0.85rem, 1.6vw, 1.15rem);
}
.lower-third .clock {
  font-family: var(--font-display);
  color: var(--gold-light);
  font-variant-numeric: tabular-nums;
}
.lt-enter-active,
.lt-leave-active {
  transition: all 0.35s ease;
}
.lt-enter-from,
.lt-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
@media (prefers-reduced-motion: reduce) {
  .player,
  .ball {
    transition: none;
  }
  .halo {
    animation: none;
  }
}
</style>
