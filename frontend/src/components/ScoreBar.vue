<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMatch } from '@/stores/match'
import { useView } from '@/stores/view'

const { t } = useI18n()
const match = useMatch()
const view = useView()

const momentum = computed(() => match.stats?.momentum ?? 0) // -1 away .. +1 home
const rhythm = computed(() => match.stats?.rhythm ?? 'balanced')
// The meter fills from the centre toward whoever is on top.
const meter = computed(() => ({ left: `${50 - Math.max(0, momentum.value) * 50}%`, right: `${50 + Math.min(0, momentum.value) * 50}%` }))
</script>

<template>
  <header v-if="match.meta" class="score panel">
    <div class="team home" :class="{ fav: view.favSide === 'home' }">
      <span class="badge" :style="{ background: match.meta.home.primary_color, borderColor: match.meta.home.secondary_color }" />
      <span class="name">{{ match.meta.home.name }}</span>
    </div>
    <div class="center">
      <div class="result" aria-live="polite">
        <span>{{ match.score.home }}</span><span class="sep">-</span><span>{{ match.score.away }}</span>
      </div>
      <div class="clock">
        <span class="status" :class="match.status">{{ t(`status.${match.status}`) }}</span>
        {{ match.clock }}
      </div>
    </div>
    <div class="team away" :class="{ fav: view.favSide === 'away' }">
      <span class="name">{{ match.meta.away.name }}</span>
      <span class="badge" :style="{ background: match.meta.away.primary_color, borderColor: match.meta.away.secondary_color }" />
    </div>
    <div class="meter" :title="`${t('momentum.title')}: ${momentum}`">
      <div class="fill home" :style="{ left: meter.left, right: '50%', background: match.meta.home.primary_color }" />
      <div class="fill away" :style="{ left: '50%', right: meter.right, background: match.meta.away.primary_color }" />
      <span class="rhythm" :class="rhythm">{{ t(`momentum.${rhythm}`) }}</span>
    </div>
  </header>
</template>

<style scoped>
.score {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 10px 14px 16px;
  position: relative;
}
.team {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  min-width: 0;
}
.team.away {
  justify-content: flex-end;
}
.team .name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.team.fav .name::after {
  content: ' ★';
  color: var(--accent-2);
}
.badge {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 3px solid;
  flex: none;
}
.center {
  text-align: center;
}
.result {
  font-size: 2rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.sep {
  margin: 0 8px;
  color: var(--muted);
}
.clock {
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  font-size: 0.85rem;
  margin-top: 4px;
}
.status {
  font-weight: 800;
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 6px;
  background: var(--panel-2);
}
.status.live {
  background: var(--danger);
  color: #fff;
}
.meter {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 6px;
  height: 4px;
  background: var(--panel-2);
  border-radius: 2px;
}
.fill {
  position: absolute;
  top: 0;
  bottom: 0;
  transition: all 0.8s ease;
}
.rhythm {
  position: absolute;
  right: 0;
  top: -16px;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.rhythm.chaos {
  color: var(--warn);
}
.rhythm.control {
  color: var(--accent);
}
@media (max-width: 560px) {
  .team .name {
    font-size: 0.85rem;
  }
  .result {
    font-size: 1.5rem;
  }
}
</style>
