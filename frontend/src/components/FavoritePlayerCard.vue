<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
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
  <section v-if="player" class="panel fav" :style="{ borderColor: player.club.primary_color }">
    <h2>⭐ {{ t('fav.title') }}</h2>
    <div class="who">
      <span class="shirt" :style="{ background: player.club.primary_color, color: player.club.secondary_color }">{{ player.number }}</span>
      <div>
        <strong>{{ player.name }}</strong>
        <div class="muted small">{{ player.club.name }} · {{ player.position }}<span v-if="!onPitch && match.events.length"> · 🪑</span></div>
      </div>
    </div>
    <dl class="grid">
      <div v-for="i in items" :key="i.k">
        <dt>{{ t(`fav.${i.k}`) }}</dt>
        <dd>{{ i.v }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.fav {
  border-width: 2px;
}
.who {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.shirt {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-weight: 800;
}
.small {
  font-size: 0.8rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
  margin: 0;
}
dt {
  font-size: 0.7rem;
  color: var(--muted);
}
dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
</style>
