<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AgentError, askMatch, fetchCatchup } from '@/api/client'
import type { CommentaryLine } from '@/api/types'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()
const question = ref('')
const loading = ref(false)
const asking = ref(false)
const error = ref('')
let lastCatchup = 0
let seq = 0

function chatLine(speaker: 'system' | 'narrator', text: string, source: 'template' | 'ai'): CommentaryLine {
  return {
    id: `qa-${Date.now()}-${seq++}`,
    elapsed: match.elapsed,
    clock: match.clock,
    speaker,
    level: 1, // a reply to the viewer always shows, and the voice reads it
    lang: profile.lang,
    text,
    emotion: 'neutral',
    source,
  }
}

async function ask() {
  const o = match.options
  const q = question.value.trim()
  if (!o || q.length < 2 || asking.value) return
  asking.value = true
  error.value = ''
  match.pushLine(chatLine('system', `❓ ${q}`, 'template'))
  question.value = ''
  try {
    const res = await askMatch(o, q, match.elapsed / 60, profile.lang, profile.club)
    match.pushLine(chatLine('narrator', res.answer, res.source === 'ai' ? 'ai' : 'template'))
  } catch (err) {
    error.value = t(err instanceof AgentError && err.status === 503 ? 'chat.askOff' : 'chat.askError')
  } finally {
    asking.value = false
  }
}

async function catchUp() {
  const o = match.options
  if (!o) return
  loading.value = true
  try {
    // From the last catch-up, or the last 15 minutes of play.
    const since = Math.max(lastCatchup, match.elapsed - 15 * 60, 0)
    match.recap = await fetchCatchup(o, match.elapsed, since, profile.lang, profile.club, profile.ai)
    lastCatchup = match.elapsed
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="ask">
    <form class="row" @submit.prevent="ask">
      <label class="sr-only" for="ask-input">{{ t('chat.ask') }}</label>
      <input
        id="ask-input"
        v-model="question"
        type="text"
        maxlength="300"
        :placeholder="t('chat.ask')"
        :disabled="!match.events.length || asking"
      />
      <button type="submit" :disabled="!match.events.length || asking || question.trim().length < 2">
        {{ asking ? '…' : '▶' }}
      </button>
    </form>
    <small v-if="asking" class="muted" role="status">{{ t('chat.thinking') }}</small>
    <small v-else-if="error" class="error" role="alert">{{ error }}</small>
    <button class="catchup" :disabled="!match.events.length || loading" @click="catchUp">
      ⏪ {{ t('chat.catchup') }}
    </button>
  </div>
</template>

<style scoped>
.ask {
  display: grid;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.row {
  display: flex;
  gap: 6px;
}
.row input {
  flex: 1;
  min-width: 0;
}
.catchup {
  justify-self: start;
}
.error {
  color: var(--danger);
}
</style>
