<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import InputGroup from 'primevue/inputgroup'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { AgentError, exportUrl, queryMatch } from '@/api/client'
import AppPanel from '@/components/AppPanel.vue'
import { playerStats, type LivePlayerStats } from '@/lib/playerStats'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import { useView, type Layer } from '@/stores/view'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()
const view = useView()

const LAYERS: Layer[] = ['none', 'shot_map', 'heatmap', 'progressive']
const layerOptions = computed(() => LAYERS.map((l) => ({ value: l, label: t(l === 'none' ? 'analyst.none' : `analyst.${l}`) })))

const request = ref('')
const querying = ref(false)
const queryError = ref('')

async function runQuery() {
  const o = match.options
  const q = request.value.trim()
  if (!o || q.length < 2 || querying.value) return
  querying.value = true
  queryError.value = ''
  try {
    const res = await queryMatch(o, q, match.elapsed / 60, profile.lang)
    if (res.overlay) {
      view.applyOverlay(res.overlay)
      if (res.message) queryError.value = res.message
    } else {
      queryError.value = res.message
    }
  } catch (err) {
    queryError.value = t(err instanceof AgentError && err.status === 503 ? 'chat.askOff' : 'chat.askError')
  } finally {
    querying.value = false
  }
}

const label = (p: { number: number; name: string; club: string }) => `#${p.number} ${p.name} (${p.club})`
const allPlayers = computed(() => {
  const m = match.meta
  if (!m) return []
  return [
    ...m.home.squad.map((p) => ({ ...p, side: 'home' as const, club: m.home.short_name })),
    ...m.away.squad.map((p) => ({ ...p, side: 'away' as const, club: m.away.short_name })),
  ].map((p) => ({ ...p, label: label(p) }))
})
const players = computed(() => allPlayers.value.filter((p) => view.layerTeam === 'both' || p.side === view.layerTeam))
const teamOptions = computed(() => [
  { value: 'both', label: t('analyst.both') },
  { value: 'home', label: match.meta?.home.short_name ?? '' },
  { value: 'away', label: match.meta?.away.short_name ?? '' },
])

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
const fmt = (v: number | string) => (typeof v === 'number' ? +v.toFixed(2) : v)
</script>

<template>
  <AppPanel :title="t('analyst.title')" icon="pi-chart-bar">
    <div class="grid gap-3">
      <form class="grid gap-1.5" @submit.prevent="runQuery">
        <InputGroup>
          <InputText
            v-model="request"
            maxlength="300"
            :placeholder="t('analyst.query')"
            :aria-label="t('analyst.query')"
            :disabled="!match.events.length || querying"
            fluid
          />
          <Button
            type="submit"
            icon="pi pi-sparkles"
            :aria-label="t('analyst.run')"
            :loading="querying"
            :disabled="!match.events.length || querying || request.trim().length < 2"
          />
        </InputGroup>
        <div v-if="querying" role="status" class="grid gap-1">
          <ProgressBar mode="indeterminate" class="!h-1" />
          <small class="text-muted">{{ t('analyst.querying') }}</small>
        </div>
        <Message v-else-if="queryError" severity="warn" size="small" :closable="false">{{ queryError }}</Message>
        <Chip
          v-else-if="view.overlay"
          :label="`${view.overlay.title} · ${view.overlay.count} ${t('analyst.events')}`"
          icon="pi pi-sparkles"
          removable
          class="!max-w-full !bg-raised"
          @remove="view.clearOverlay()"
        />
      </form>

      <fieldset class="m-0 grid gap-2 rounded-xl border border-line px-2.5 pb-2.5 pt-1">
        <legend class="px-1 text-xs text-muted">{{ t('analyst.layers') }}</legend>
        <SelectButton
          :model-value="view.layer"
          :options="layerOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          size="small"
          :aria-label="t('analyst.layers')"
          @update:model-value="(l: Layer) => view.setLayer(l)"
        />
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="grid gap-0.5 text-xs text-muted">
            {{ t('analyst.team') }}
            <Select v-model="view.layerTeam" :options="teamOptions" option-label="label" option-value="value" fluid />
          </label>
          <label class="grid gap-0.5 text-xs text-muted">
            {{ t('analyst.player') }}
            <Select
              v-model="view.layerPlayer"
              :options="players"
              option-label="label"
              option-value="id"
              :placeholder="t('analyst.allPlayers')"
              show-clear
              filter
              fluid
            />
          </label>
        </div>
      </fieldset>

      <fieldset class="m-0 grid gap-2 rounded-xl border border-line px-2.5 pb-2.5 pt-1">
        <legend class="px-1 text-xs text-muted">{{ t('analyst.compare') }}</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <Select
            v-model="view.compareA"
            :options="allPlayers"
            option-label="label"
            option-value="id"
            :placeholder="`${t('analyst.player')} A`"
            :aria-label="`${t('analyst.player')} A`"
            show-clear
            filter
            fluid
          />
          <Select
            v-model="view.compareB"
            :options="allPlayers"
            option-label="label"
            option-value="id"
            :placeholder="`${t('analyst.player')} B`"
            :aria-label="`${t('analyst.player')} B`"
            show-clear
            filter
            fluid
          />
        </div>
        <table v-if="view.compareA || view.compareB" class="w-full border-collapse tabular-nums">
          <tbody>
            <tr v-for="r in compare" :key="r.k">
              <td class="w-[30%] text-center font-bold" :class="{ 'text-lime': r.a > r.b }">{{ fmt(r.a) }}</td>
              <th class="text-xs font-normal text-muted">{{ t(r.label) }}</th>
              <td class="w-[30%] text-center font-bold" :class="{ 'text-lime': r.b > r.a }">{{ fmt(r.b) }}</td>
            </tr>
          </tbody>
        </table>
      </fieldset>

      <div v-if="match.options" class="flex flex-wrap items-center gap-1.5">
        <span class="text-muted">{{ t('analyst.export') }}</span>
        <Button as="a" :href="exportUrl(match.options, 'csv')" download label="CSV" icon="pi pi-download" text size="small" />
        <Button as="a" :href="exportUrl(match.options, 'json')" download label="JSON" icon="pi pi-download" text size="small" />
      </div>
    </div>
  </AppPanel>
</template>
