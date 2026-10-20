<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { exportUrl } from '@/api/client'
import { playerStats, type LivePlayerStats } from '@/lib/playerStats'
import { useMatch } from '@/stores/match'
import { useView, type Layer } from '@/stores/view'

const { t } = useI18n()
const match = useMatch()
const view = useView()

const LAYERS: Layer[] = ['none', 'shot_map', 'heatmap', 'progressive']

const players = computed(() => {
  const m = match.meta
  if (!m) return []
  return [
    ...m.home.squad.map((p) => ({ ...p, side: 'home' as const, club: m.home.short_name })),
    ...m.away.squad.map((p) => ({ ...p, side: 'away' as const, club: m.away.short_name })),
  ].filter((p) => view.layerTeam === 'both' || p.side === view.layerTeam)
})
const allPlayers = computed(() => {
  const m = match.meta
  if (!m) return []
  return [...m.home.squad.map((p) => ({ ...p, club: m.home.short_name })), ...m.away.squad.map((p) => ({ ...p, club: m.away.short_name }))]
})

const ROWS: { k: keyof LivePlayerStats; label: string }[] = [
  { k: 'touches', label: 'fav.touches' },
  { k: 'passesCompleted', label: 'fav.passes' },
  { k: 'shots', label: 'fav.shots' },
  { k: 'xg', label: 'stats.xg' },
  { k: 'goals', label: 'fav.goals' },
  { k: 'sprints', label: 'fav.sprints' },
  { k: 'topSpeed', label: 'fav.topSpeed' },
  { k: 'regains', label: 'fav.tackles' },
]
const compare = computed(() => {
  const a = playerStats(match.events, view.compareA)
  const b = playerStats(match.events, view.compareB)
  return ROWS.map((r) => ({ ...r, a: a[r.k], b: b[r.k] }))
})
</script>

<template>
  <section class="panel analyst">
    <h2>📊 {{ t('analyst.title') }}</h2>

    <div class="query">
      <input type="text" :placeholder="t('analyst.query')" disabled :title="t('analyst.querySoon')" />
      <small class="muted">{{ t('analyst.querySoon') }}</small>
    </div>

    <fieldset>
      <legend>{{ t('analyst.layers') }}</legend>
      <div class="chips">
        <button
          v-for="l in LAYERS"
          :key="l"
          :class="{ active: view.layer === l }"
          :aria-pressed="view.layer === l"
          @click="view.layer = l"
        >
          {{ t(l === 'none' ? 'analyst.none' : `analyst.${l}`) }}
        </button>
      </div>
      <div class="filters">
        <label>
          {{ t('analyst.team') }}
          <select v-model="view.layerTeam">
            <option value="both">{{ t('analyst.both') }}</option>
            <option value="home">{{ match.meta?.home.short_name }}</option>
            <option value="away">{{ match.meta?.away.short_name }}</option>
          </select>
        </label>
        <label>
          {{ t('analyst.player') }}
          <select v-model="view.layerPlayer">
            <option :value="null">{{ t('analyst.allPlayers') }}</option>
            <option v-for="p in players" :key="p.id" :value="p.id">#{{ p.number }} {{ p.name }} ({{ p.club }})</option>
          </select>
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>{{ t('analyst.compare') }}</legend>
      <div class="filters">
        <select v-model="view.compareA" :aria-label="`${t('analyst.player')} A`">
          <option :value="null">—</option>
          <option v-for="p in allPlayers" :key="p.id" :value="p.id">#{{ p.number }} {{ p.name }} ({{ p.club }})</option>
        </select>
        <select v-model="view.compareB" :aria-label="`${t('analyst.player')} B`">
          <option :value="null">—</option>
          <option v-for="p in allPlayers" :key="p.id" :value="p.id">#{{ p.number }} {{ p.name }} ({{ p.club }})</option>
        </select>
      </div>
      <table v-if="view.compareA || view.compareB" class="cmp">
        <tbody>
          <tr v-for="r in compare" :key="r.k">
            <td :class="{ win: r.a > r.b }">{{ typeof r.a === 'number' ? +r.a.toFixed(2) : r.a }}</td>
            <th>{{ t(r.label) }}</th>
            <td :class="{ win: r.b > r.a }">{{ typeof r.b === 'number' ? +r.b.toFixed(2) : r.b }}</td>
          </tr>
        </tbody>
      </table>
    </fieldset>

    <div v-if="match.options" class="export">
      <span class="muted">{{ t('analyst.export') }}:</span>
      <a :href="exportUrl(match.options, 'csv')" download>CSV</a>
      <a :href="exportUrl(match.options, 'json')" download>JSON</a>
    </div>
  </section>
</template>

<style scoped>
.analyst {
  display: grid;
  gap: 12px;
}
.query {
  display: grid;
  gap: 4px;
}
.query small {
  font-size: 0.7rem;
}
fieldset {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 10px 10px;
  margin: 0;
}
legend {
  font-size: 0.75rem;
  color: var(--muted);
  padding: 0 4px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chips button {
  font-size: 0.8rem;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
.filters label {
  display: grid;
  gap: 2px;
  font-size: 0.75rem;
  color: var(--muted);
}
.filters select {
  max-width: 100%;
}
.cmp {
  width: 100%;
  margin-top: 8px;
  font-variant-numeric: tabular-nums;
  border-collapse: collapse;
}
.cmp th {
  font-weight: 400;
  color: var(--muted);
  font-size: 0.75rem;
}
.cmp td {
  width: 30%;
  text-align: center;
  font-weight: 700;
}
.cmp td.win {
  color: var(--accent-2);
}
.export {
  display: flex;
  gap: 10px;
  align-items: center;
}
.export a {
  color: var(--accent);
}
</style>
