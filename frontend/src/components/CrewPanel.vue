<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import type { CrewStatus } from '@/api/types'
import AppPanel from '@/components/AppPanel.vue'
import { useMatch } from '@/stores/match'

const { t } = useI18n()
const match = useMatch()

const AGENTS: CrewStatus['agent'][] = ['explainer', 'commentator', 'recapper']
type Severity = 'success' | 'warn' | 'danger' | 'secondary'
const SEVERITY: Record<CrewStatus['status'], Severity> = {
  ok: 'success',
  fallback: 'warn',
  degraded: 'warn',
  error: 'danger',
  disabled: 'danger',
  skipped: 'secondary',
}

const rows = computed(() =>
  AGENTS.map((agent) => {
    const done = match.crew.filter((c) => c.agent === agent)
    const timed = done.filter((c) => c.latency_ms != null)
    const avg = timed.length ? Math.round(timed.reduce((s, c) => s + (c.latency_ms ?? 0), 0) / timed.length) : null
    return {
      agent,
      handled: done.filter((c) => c.status === 'ok' || c.status === 'fallback').length,
      fallbacks: done.filter((c) => c.status === 'fallback' || c.status === 'error').length,
      avg,
      last: done[done.length - 1] ?? null,
    }
  }),
)

const recent = computed(() => match.crew.slice(-6).reverse())
const seconds = (ms: number) => `${(ms / 1000).toFixed(1)} s`
</script>

<template>
  <AppPanel :title="t('crew.title')" icon="pi-sparkles">
    <Message v-if="match.crewDisabled" severity="info" size="small" :closable="false">{{ t('crew.disabledWhy') }}</Message>
    <template v-else>
      <div class="grid gap-2.5 [grid-template-columns:repeat(auto-fit,minmax(140px,1fr))]">
        <div v-for="r in rows" :key="r.agent" class="rounded-lg border border-line p-2.5">
          <div class="flex flex-wrap items-center gap-1.5">
            <strong>{{ t(`crew.${r.agent}`) }}</strong>
            <Tag
              v-if="r.last"
              :value="t(`crew.${r.last.status}`)"
              :severity="SEVERITY[r.last.status]"
              class="!px-1.5 !py-0 !text-[0.65rem]"
            />
          </div>
          <dl class="mb-0 mt-1.5 grid gap-0.5 text-sm">
            <div class="flex justify-between">
              <dt class="text-muted">{{ t('crew.handled') }}</dt>
              <dd class="m-0 tabular-nums">{{ r.handled }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-muted">{{ t('crew.fallbacks') }}</dt>
              <dd class="m-0 tabular-nums">{{ r.fallbacks }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-muted">{{ t('crew.avg') }}</dt>
              <dd class="m-0 tabular-nums">{{ r.avg == null ? '–' : seconds(r.avg) }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <p v-if="!match.crew.length" class="m-0 text-muted">{{ t('crew.waiting') }}</p>
      <ul v-else class="m-0 mt-2.5 grid list-none gap-1 p-0 text-sm">
        <li
          v-for="c in recent"
          :key="`${c.agent}-${c.moment_id}`"
          class="flex flex-wrap items-center gap-1.5"
          :title="c.problems?.join(' · ')"
        >
          <Tag :value="t(`crew.${c.status}`)" :severity="SEVERITY[c.status]" class="!px-1.5 !py-0 !text-[0.65rem]" />
          <span class="text-muted tabular-nums">{{ c.moment_id }}</span>
          <span>{{ t(`crew.${c.agent}`) }}</span>
          <span class="text-muted">
            {{ c.attempts }} {{ t('crew.attempts') }}<template v-if="c.latency_ms != null"> · {{ seconds(c.latency_ms) }}</template>
          </span>
        </li>
      </ul>
    </template>
  </AppPanel>
</template>
