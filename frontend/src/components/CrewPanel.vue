<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CrewStatus } from '@/api/types'
import { useMatch } from '@/stores/match'

const { t } = useI18n()
const match = useMatch()

const AGENTS: CrewStatus['agent'][] = ['explainer', 'commentator']

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
</script>

<template>
  <section class="crew panel" :aria-label="t('crew.title')">
    <h2>🤖 {{ t('crew.title') }}</h2>
    <p v-if="match.crewDisabled" class="muted">{{ t('crew.disabledWhy', { reason: match.crewDisabled }) }}</p>
    <template v-else>
      <div class="agents">
        <div v-for="r in rows" :key="r.agent" class="agent">
          <div class="name">
            <span class="dot" :class="r.last?.status ?? 'idle'" aria-hidden="true" />
            <strong>{{ t(`crew.${r.agent}`) }}</strong>
            <span v-if="r.last" class="pill" :class="r.last.status">{{ t(`crew.${r.last.status}`) }}</span>
          </div>
          <dl>
            <div><dt>{{ t('crew.handled') }}</dt><dd>{{ r.handled }}</dd></div>
            <div><dt>{{ t('crew.fallbacks') }}</dt><dd>{{ r.fallbacks }}</dd></div>
            <div><dt>{{ t('crew.avg') }}</dt><dd>{{ r.avg == null ? '–' : `${(r.avg / 1000).toFixed(1)} s` }}</dd></div>
          </dl>
        </div>
      </div>
      <p v-if="!match.crew.length" class="muted">{{ t('crew.waiting') }}</p>
      <ul v-else class="log">
        <li v-for="c in recent" :key="`${c.agent}-${c.moment_id}`" :title="c.problems?.join(' · ')">
          <span class="dot" :class="c.status" aria-hidden="true" />
          <span class="mid">{{ c.moment_id }}</span>
          <span>{{ t(`crew.${c.agent}`) }}</span>
          <span class="muted">{{ t(`crew.${c.status}`) }} · {{ c.attempts }} {{ t('crew.attempts') }}<template v-if="c.latency_ms != null"> · {{ (c.latency_ms / 1000).toFixed(1) }} s</template></span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 8px;
}
.agents {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.agent {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 10px;
}
.name {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
dl {
  margin: 6px 0 0;
  display: grid;
  gap: 2px;
  font-size: 0.8rem;
}
dl div {
  display: flex;
  justify-content: space-between;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
  flex: none;
}
.dot.ok {
  background: var(--accent-2);
}
.dot.fallback,
.dot.degraded {
  background: #e0a526;
}
.dot.error,
.dot.disabled {
  background: var(--danger);
}
.pill {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 6px;
  font-size: 0.65rem;
}
.pill.ok {
  border-color: var(--accent-2);
  color: var(--accent-2);
}
.pill.error {
  border-color: var(--danger);
  color: var(--danger);
}
.log {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: grid;
  gap: 3px;
  font-size: 0.78rem;
}
.log li {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.mid {
  font-variant-numeric: tabular-nums;
  color: var(--muted);
}
</style>
