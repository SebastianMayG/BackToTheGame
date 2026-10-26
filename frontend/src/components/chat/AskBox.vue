<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputGroup from 'primevue/inputgroup'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
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
    favourite: false,
  }
}

async function ask() {
  const o = match.options
  const q = question.value.trim()
  if (!o || q.length < 2 || asking.value) return
  asking.value = true
  error.value = ''
  match.pushLine(chatLine('system', `${t('chat.you')}: ${q}`, 'template'))
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
  <div class="grid gap-2 border-t border-line pt-2.5">
    <form @submit.prevent="ask">
      <label class="sr-only" for="ask-input">{{ t('chat.ask') }}</label>
      <InputGroup>
        <InputText
          id="ask-input"
          v-model="question"
          maxlength="300"
          :placeholder="t('chat.ask')"
          :disabled="!match.events.length || asking"
          fluid
        />
        <Button
          type="submit"
          icon="pi pi-send"
          :aria-label="t('chat.send')"
          :loading="asking"
          :disabled="!match.events.length || asking || question.trim().length < 2"
        />
      </InputGroup>
    </form>
    <div v-if="asking" role="status" class="grid gap-1">
      <ProgressBar mode="indeterminate" class="!h-1" />
      <small class="text-muted">{{ t('chat.thinking') }}</small>
    </div>
    <Message v-else-if="error" severity="error" size="small" :closable="false">{{ error }}</Message>
    <Button
      icon="pi pi-history"
      :label="t('chat.catchup')"
      severity="secondary"
      outlined
      size="small"
      class="justify-self-start"
      :loading="loading"
      :disabled="!match.events.length || loading"
      @click="catchUp"
    />
  </div>
</template>
