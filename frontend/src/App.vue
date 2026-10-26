<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import ToggleButton from 'primevue/togglebutton'
import type { Lang, Mode } from '@/api/types'
import { useVoice } from '@/composables/useVoice'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import { useView, type Layer } from '@/stores/view'
import AnalystPanel from '@/components/AnalystPanel.vue'
import CommentaryChat from '@/components/chat/CommentaryChat.vue'
import CrewPanel from '@/components/CrewPanel.vue'
import FavoritePlayerCard from '@/components/FavoritePlayerCard.vue'
import MomentumChart from '@/components/MomentumChart.vue'
import PitchView from '@/components/pitch/PitchView.vue'
import RecapModal from '@/components/RecapModal.vue'
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
  view.clearOverlay()
  profile.newSeed() // every match is a different one
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
  (m) => {
    // Accessible mode is the only dark theme: black background, white lines, yellow accent.
    document.documentElement.classList.toggle('accessible', m === 'accessible')
    document.documentElement.classList.toggle('app-dark', m === 'accessible')
  },
  { immediate: true },
)

const MODES: Mode[] = ['fan', 'analyst', 'accessible']
const modeOptions = computed(() => MODES.map((m) => ({ value: m, label: t(`mode.${m}`) })))
const langOptions = [
  { value: 'en', label: 'EN' },
  { value: 'es', label: 'ES' },
]

// Shareable demo links, e.g. /?mode=analyst&club=NVR&player=NVR-9&lang=en&seed=42&autostart=1
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
  if (q.has('ai')) profile.ai = !['0', 'false', 'off'].includes(q.get('ai') ?? '')
  const layer = q.get('layer') as Layer | null
  if (layer && ['none', 'shot_map', 'heatmap', 'progressive'].includes(layer)) view.layer = layer
  if (q.has('autostart')) start()
})
</script>

<template>
  <SetupScreen v-if="!inMatch" @start="start" />

  <div
    v-else
    class="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 gap-3.5 p-3.5 max-lg:p-2.5 lg:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)]"
  >
    <div class="flex min-w-0 flex-col gap-2.5">
      <ScoreBar />
      <PitchView />
      <Timeline />

      <div class="flex flex-wrap items-center gap-2" role="toolbar">
        <SelectButton
          v-model="profile.mode"
          :options="modeOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          size="small"
          :aria-label="t('setup.mode')"
        />
        <SelectButton
          v-model="profile.lang"
          :options="langOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          size="small"
          :aria-label="t('setup.lang')"
        />
        <ToggleButton
          v-model="profile.voice"
          on-icon="pi pi-volume-up"
          off-icon="pi pi-volume-off"
          :on-label="t('controls.voice')"
          :off-label="t('controls.voice')"
          :disabled="!voice.supported"
          size="small"
        />
        <ToggleButton
          v-model="profile.names"
          on-icon="pi pi-tag"
          off-icon="pi pi-tag"
          :on-label="t('controls.names')"
          :off-label="t('controls.names')"
          size="small"
        />
        <span class="flex-1" />
        <Button icon="pi pi-refresh" :label="t('controls.restart')" severity="secondary" outlined size="small" @click="newMatch" />
      </div>

      <div class="grid items-start gap-2.5 [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
        <FavoritePlayerCard v-if="profile.player" />
        <CrewPanel v-if="profile.ai" />
        <AnalystPanel v-if="profile.mode === 'analyst'" />
        <MomentumChart />
        <StatsPanel />
      </div>
    </div>

    <div class="min-h-0 max-lg:h-[70vh] lg:sticky lg:top-3.5 lg:h-[calc(100vh-1.75rem)]">
      <CommentaryChat />
    </div>

    <RecapModal />
  </div>
</template>
