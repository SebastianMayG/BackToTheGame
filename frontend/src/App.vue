<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Lang, Mode } from '@/api/types'
import { useVoice } from '@/composables/useVoice'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import { useView, type Layer } from '@/stores/view'
import AnalystPanel from '@/components/AnalystPanel.vue'
import CommentaryChat from '@/components/chat/CommentaryChat.vue'
import FavoritePlayerCard from '@/components/FavoritePlayerCard.vue'
import MomentumChart from '@/components/MomentumChart.vue'
import PitchView from '@/components/pitch/PitchView.vue'
import RecapModal from '@/components/RecapModal.vue'
import CrewPanel from '@/components/CrewPanel.vue'
import ScoreBar from '@/components/ScoreBar.vue'
import SetupScreen from '@/components/SetupScreen.vue'
import StatsPanel from '@/components/StatsPanel.vue'
import Timeline from '@/components/Timeline.vue'

const { t, locale } = useI18n()
const profile = useProfile()
const match = useMatch()
const voice = useVoice()
const view = useView()

const inMatch = computed(() => match.status !== 'idle' || match.events.length > 0)

function streamOptions() {
  return {
    seed: profile.seed,
    home: profile.home,
    away: profile.away,
    speed: profile.speed,
    lang: profile.lang,
    mode: profile.mode,
    club: profile.club,
    player: profile.player,
    ai: profile.ai,
  }
}

function start() {
  match.start(streamOptions())
}

function newMatch() {
  match.stop()
  voice.cancel()
  match.reset()
  match.status = 'idle'
}

// Language or mode changed mid-match: reconnect and carry on from the last event.
watch(
  () => [profile.lang, profile.mode] as [Lang, Mode],
  () => {
    // Only resume once events have arrived; before that the stream simply starts with the new profile.
    if ((match.status === 'live' || match.status === 'connecting') && match.events.length) {
      match.start(streamOptions(), true)
    }
  },
)

watch(
  () => profile.lang,
  (l) => {
    locale.value = l
    document.documentElement.lang = l
  },
  { immediate: true },
)
watch(
  () => profile.mode,
  (m) => document.documentElement.classList.toggle('accessible', m === 'accessible'),
  { immediate: true },
)

const MODES: Mode[] = ['fan', 'analyst', 'accessible']

// Shareable demo links, e.g. /?mode=analyst&club=NVR&player=NVR-9&lang=en&autostart=1
onMounted(() => {
  const q = new URLSearchParams(window.location.search)
  const str = (k: string) => q.get(k) || null
  if (str('home')) profile.home = str('home')!
  if (str('away')) profile.away = str('away')!
  if (str('seed')) profile.seed = Number(q.get('seed'))
  if (str('speed')) profile.speed = Number(q.get('speed'))
  if (q.get('lang') === 'es' || q.get('lang') === 'en') profile.lang = q.get('lang') as Lang
  if (MODES.includes(q.get('mode') as Mode)) profile.mode = q.get('mode') as Mode
  if (q.has('club')) profile.club = str('club')
  if (q.has('player')) profile.player = str('player')
  if (q.has('ai')) profile.ai = q.get('ai') !== '0'
  const layer = q.get('layer') as Layer | null
  if (layer && ['none', 'shot_map', 'heatmap', 'progressive'].includes(layer)) view.layer = layer
  if (q.has('autostart')) start()
})
</script>

<template>
  <SetupScreen v-if="!inMatch" @start="start" />

  <div v-else class="studio">
    <div class="left">
      <ScoreBar />
      <PitchView />
      <Timeline />
      <div class="controls" role="toolbar">
        <div class="seg" role="group" :aria-label="t('setup.mode')">
          <button v-for="m in MODES" :key="m" :class="{ active: profile.mode === m }" :aria-pressed="profile.mode === m" @click="profile.mode = m">
            {{ t(`mode.${m}`) }}
          </button>
        </div>
        <div class="seg" role="group" :aria-label="t('setup.lang')">
          <button v-for="l in ['es', 'en'] as Lang[]" :key="l" :class="{ active: profile.lang === l }" :aria-pressed="profile.lang === l" @click="profile.lang = l">
            {{ l.toUpperCase() }}
          </button>
        </div>
        <button :class="{ active: profile.voice }" :aria-pressed="profile.voice" :disabled="!voice.supported" @click="profile.voice = !profile.voice">
          {{ profile.voice ? '🔊' : '🔇' }} {{ t('controls.voice') }}
        </button>
        <button :class="{ active: profile.names }" :aria-pressed="profile.names" @click="profile.names = !profile.names">
          🏷️ {{ t('controls.names') }}
        </button>
        <span class="spacer" />
        <button @click="newMatch">↺ {{ t('controls.restart') }}</button>
      </div>

      <div class="panels">
        <FavoritePlayerCard v-if="profile.player" />
        <CrewPanel v-if="profile.ai" />
        <AnalystPanel v-if="profile.mode === 'analyst'" />
        <MomentumChart />
        <StatsPanel />
      </div>
    </div>

    <div class="right">
      <CommentaryChat />
    </div>

    <RecapModal />
  </div>
</template>

<style scoped>
.studio {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 1fr);
  gap: 14px;
  padding: 14px;
  max-width: 1600px;
  margin: 0 auto;
  min-height: 100vh;
}
.left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.right {
  position: sticky;
  top: 14px;
  height: calc(100vh - 28px);
  min-height: 0;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.seg {
  display: flex;
}
.seg button {
  border-radius: 0;
}
.seg button:first-child {
  border-radius: 8px 0 0 8px;
}
.seg button:last-child {
  border-radius: 0 8px 8px 0;
}
.spacer {
  flex: 1;
}
.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 10px;
  align-items: start;
}
@media (max-width: 900px) {
  .studio {
    grid-template-columns: 1fr;
    padding: 10px;
  }
  .right {
    position: static;
    height: 70vh;
  }
}
</style>
