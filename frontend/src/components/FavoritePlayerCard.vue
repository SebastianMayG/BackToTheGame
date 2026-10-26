<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Avatar from 'primevue/avatar'
import Tag from 'primevue/tag'
import AppPanel from '@/components/AppPanel.vue'
import { playerStats } from '@/lib/playerStats'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()

const player = computed(() => {
  const m = match.meta
  if (!m || !profile.player) return null
  for (const club of [m.home, m.away]) {
    const p = club.squad.find((x) => x.id === profile.player)
    if (p) return { ...p, club }
  }
  return null
})
const onPitch = computed(() =>
  [...Object.values(match.lineups.home), ...Object.values(match.lineups.away)].some((p) => p.id === profile.player),
)
const s = computed(() => playerStats(match.events, profile.player))
const items = computed(() => [
  { k: 'touches', v: s.value.touches },
  { k: 'passes', v: `${s.value.passesCompleted}/${s.value.passes}` },
  { k: 'shots', v: `${s.value.shots} (xG ${s.value.xg})` },
  { k: 'goals', v: s.value.goals },
  { k: 'sprints', v: s.value.sprints },
  { k: 'topSpeed', v: s.value.topSpeed ? `${s.value.topSpeed.toFixed(1)} km/h` : '—' },
  { k: 'distance', v: `${s.value.carryDistance} m` },
  { k: 'tackles', v: s.value.regains },
])
</script>

<template>
  <AppPanel
    v-if="player"
    :title="t('fav.title')"
    icon="pi-star-fill"
    :style="{ borderColor: player.club.primary_color, borderWidth: '2px' }"
  >
    <div class="mb-2.5 flex items-center gap-2.5">
      <Avatar
        :label="String(player.number)"
        shape="square"
        size="large"
        :style="{ background: player.club.primary_color, color: player.club.secondary_color, fontWeight: 800 }"
      />
      <div>
        <strong>{{ player.name }}</strong>
        <div class="flex flex-wrap items-center gap-1.5 text-sm text-muted">
          {{ player.club.name }} · {{ player.position }}
          <Tag v-if="!onPitch && match.events.length" :value="t('fav.bench')" severity="secondary" class="!px-1.5 !py-0 !text-[0.65rem]" />
        </div>
      </div>
    </div>
    <dl class="m-0 grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(110px,1fr))]">
      <div v-for="i in items" :key="i.k">
        <dt class="text-xs text-muted">{{ t(`fav.${i.k}`) }}</dt>
        <dd class="m-0 font-bold tabular-nums">{{ i.v }}</dd>
      </div>
    </dl>
  </AppPanel>
</template>
