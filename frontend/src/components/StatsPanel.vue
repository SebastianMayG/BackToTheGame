<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { TeamStats } from '@/api/types'
import AppPanel from '@/components/AppPanel.vue'
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
  <AppPanel v-if="match.stats && match.meta" :title="t('stats.title')" icon="pi-chart-line">
    <div class="grid gap-1.5 tabular-nums">
      <div v-for="r in rows" :key="r.key" class="grid grid-cols-[2.75rem_1fr_2.75rem] items-center">
        <span class="text-center font-bold">{{ fmt(r.h) }}</span>
        <div>
          <div class="text-center text-xs text-muted">{{ t(`stats.${r.key}`) }}</div>
          <div class="flex h-1.5 overflow-hidden rounded-[3px] bg-raised">
            <div
              class="transition-[width] duration-500 ease-out"
              :style="{ width: `${r.share}%`, background: match.meta.home.primary_color }"
            />
            <div class="flex-1" :style="{ background: match.meta.away.primary_color }" />
          </div>
        </div>
        <span class="text-center font-bold">{{ fmt(r.a) }}</span>
      </div>
    </div>

    <template v-if="match.stats.top_players.length">
      <h3 class="panel-title mt-4">{{ t('stats.topPlayers') }}</h3>
      <ol class="m-0 grid list-none gap-1 p-0">
        <li
          v-for="p in match.stats.top_players"
          :key="p.player.id"
          class="flex items-center gap-2"
          :class="{ 'text-lime': p.player.id === profile.player }"
        >
          <span class="w-8 font-extrabold tabular-nums">{{ p.rating.toFixed(1) }}</span>
          <span
            class="size-2.5 rounded-full"
            :style="{ background: p.team === 'home' ? match.meta.home.primary_color : match.meta.away.primary_color }"
          />
          {{ p.player.name }} <span class="text-muted">#{{ p.player.number }}</span>
        </li>
      </ol>
    </template>
  </AppPanel>
</template>
