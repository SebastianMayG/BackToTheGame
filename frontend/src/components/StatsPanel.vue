<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TeamStats } from '@/api/types'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()

type Row = { key: string; get: (s: TeamStats) => number | null | undefined; lowerIsBetter?: boolean }

const BASIC: Row[] = [
  { key: 'possession', get: (s) => s.possession_pct },
  { key: 'shots', get: (s) => s.shots },
  { key: 'onTarget', get: (s) => s.shots_on_target },
  { key: 'xg', get: (s) => s.xg },
  { key: 'corners', get: (s) => s.corners },
  { key: 'fouls', get: (s) => s.fouls },
  { key: 'cards', get: (s) => (s.yellow_cards ?? 0) + (s.red_cards ?? 0) },
]
const ADVANCED: Row[] = [
  { key: 'passes', get: (s) => s.passes },
  { key: 'passAcc', get: (s) => s.pass_accuracy },
  { key: 'progressive', get: (s) => s.progressive_passes },
  { key: 'boxEntries', get: (s) => s.box_entries },
  { key: 'fieldTilt', get: (s) => s.field_tilt_pct },
  { key: 'ppda', get: (s) => s.ppda, lowerIsBetter: true },
  { key: 'tackles', get: (s) => s.tackles_won },
  { key: 'interceptions', get: (s) => s.interceptions },
  { key: 'topShot', get: (s) => s.top_shot_speed_kmh },
]

const rows = computed(() => {
  const s = match.stats
  if (!s) return []
  const list = profile.mode === 'analyst' ? [...BASIC, ...ADVANCED] : BASIC
  return list.map((r) => {
    const h = r.get(s.home) ?? 0
    const a = r.get(s.away) ?? 0
    const total = h + a || 1
    let share = (h / total) * 100
    if (r.lowerIsBetter) share = 100 - share
    return { key: r.key, h, a, share }
  })
})
const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1))
</script>

<template>
  <section v-if="match.stats && match.meta" class="panel">
    <h2>{{ t('stats.title') }}</h2>
    <table class="stats">
      <tbody>
        <tr v-for="r in rows" :key="r.key">
          <td class="v">{{ fmt(r.h) }}</td>
          <td class="bar">
            <div class="label">{{ t(`stats.${r.key}`) }}</div>
            <div class="track">
              <div class="h" :style="{ width: `${r.share}%`, background: match.meta.home.primary_color }" />
              <div class="a" :style="{ background: match.meta.away.primary_color }" />
            </div>
          </td>
          <td class="v">{{ fmt(r.a) }}</td>
        </tr>
      </tbody>
    </table>
    <template v-if="match.stats.top_players.length">
      <h2 class="top">{{ t('stats.topPlayers') }}</h2>
      <ol class="players">
        <li v-for="p in match.stats.top_players" :key="p.player.id" :class="{ fav: p.player.id === profile.player }">
          <span class="rating">{{ p.rating.toFixed(1) }}</span>
          <span class="dot" :style="{ background: p.team === 'home' ? match.meta.home.primary_color : match.meta.away.primary_color }" />
          {{ p.player.name }} <span class="muted">#{{ p.player.number }}</span>
        </li>
      </ol>
    </template>
  </section>
</template>

<style scoped>
.stats {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}
td {
  padding: 3px 0;
}
.v {
  width: 44px;
  text-align: center;
  font-weight: 700;
}
.label {
  text-align: center;
  font-size: 0.72rem;
  color: var(--muted);
}
.track {
  display: flex;
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  background: var(--panel-2);
}
.track .h {
  transition: width 0.6s ease;
}
.track .a {
  flex: 1;
}
.top {
  margin-top: 14px;
}
.players {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 4px;
}
.players li {
  display: flex;
  align-items: center;
  gap: 8px;
}
.players li.fav {
  color: var(--accent-2);
}
.rating {
  font-weight: 800;
  width: 32px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
