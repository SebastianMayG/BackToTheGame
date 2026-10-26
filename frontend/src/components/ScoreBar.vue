<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import { useMatch } from '@/stores/match'
import { useView } from '@/stores/view'

const { t } = useI18n()
const match = useMatch()
const view = useView()

const momentum = computed(() => match.stats?.momentum ?? 0) // -1 away .. +1 home
const rhythm = computed(() => match.stats?.rhythm ?? 'balanced')
// The meter fills from the centre toward whoever is on top.
const meter = computed(() => ({
  left: `${50 - Math.max(0, momentum.value) * 50}%`,
  right: `${50 + Math.min(0, momentum.value) * 50}%`,
}))
const statusSeverity = computed(() =>
  ({ live: 'danger', ended: 'secondary', error: 'warn', connecting: 'info', idle: 'secondary' })[match.status] as
    | 'danger'
    | 'secondary'
    | 'warn'
    | 'info',
)
const RHYTHM_CLASS: Record<string, string> = { chaos: 'text-warn', control: 'text-primary' }
const rhythmClass = computed(() => RHYTHM_CLASS[rhythm.value] ?? 'text-muted')
</script>

<template>
  <header
    v-if="match.meta"
    class="relative grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-lg border border-line bg-panel px-3.5 pb-4 pt-2.5"
  >
    <div class="flex min-w-0 items-center gap-2.5 font-display text-xl font-bold uppercase tracking-wide">
      <span
        class="size-[18px] flex-none rounded-full border-[3px]"
        :style="{ background: match.meta.home.primary_color, borderColor: match.meta.home.secondary_color }"
      />
      <span class="truncate max-sm:text-sm">{{ match.meta.home.name }}</span>
      <i v-if="view.favSide === 'home'" class="pi pi-star-fill text-lime" :aria-label="t('fav.title')" />
    </div>

    <div class="text-center">
      <div class="font-display text-5xl font-bold leading-none tabular-nums max-sm:text-4xl" aria-live="polite">
        <span>{{ match.score.home }}</span><span class="mx-2 text-muted">-</span><span>{{ match.score.away }}</span>
      </div>
      <div class="mt-1 flex items-center justify-center gap-1.5 text-sm text-muted tabular-nums">
        <Tag :value="t(`status.${match.status}`)" :severity="statusSeverity" class="!px-1.5 !py-0 !text-[0.65rem]" />
        {{ match.clock }}
      </div>
    </div>

    <div class="flex min-w-0 items-center justify-end gap-2.5 font-display text-xl font-bold uppercase tracking-wide">
      <i v-if="view.favSide === 'away'" class="pi pi-star-fill text-lime" :aria-label="t('fav.title')" />
      <span class="truncate max-sm:text-sm">{{ match.meta.away.name }}</span>
      <span
        class="size-[18px] flex-none rounded-full border-[3px]"
        :style="{ background: match.meta.away.primary_color, borderColor: match.meta.away.secondary_color }"
      />
    </div>

    <div
      class="absolute inset-x-3.5 bottom-1.5 h-1 rounded-sm bg-raised"
      :title="`${t('momentum.title')}: ${momentum.toFixed(2)}`"
    >
      <div
        class="absolute inset-y-0 transition-all duration-700"
        :style="{ left: meter.left, right: '50%', background: match.meta.home.primary_color }"
      />
      <div
        class="absolute inset-y-0 transition-all duration-700"
        :style="{ left: '50%', right: meter.right, background: match.meta.away.primary_color }"
      />
      <span class="absolute -top-4 right-0 text-[0.65rem] uppercase tracking-wider" :class="rhythmClass">
        {{ t(`momentum.${rhythm}`) }}
      </span>
    </div>
  </header>
</template>
