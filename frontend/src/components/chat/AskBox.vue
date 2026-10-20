<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchCatchup } from '@/api/client'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()
const question = ref('')
const loading = ref(false)
let lastCatchup = 0

async function catchUp() {
  const o = match.options
  if (!o) return
  loading.value = true
  try {
    // From the last catch-up, or the last 15 minutes of play.
    const since = Math.max(lastCatchup, match.elapsed - 15 * 60, 0)
    match.recap = await fetchCatchup(o, match.elapsed, since, profile.lang, profile.club)
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
    <form class="row" @submit.prevent>
      <label class="sr-only" for="ask-input">{{ t('chat.ask') }}</label>
      <input id="ask-input" v-model="question" type="text" :placeholder="t('chat.ask')" disabled :title="t('chat.askSoon')" />
      <button type="submit" disabled :title="t('chat.askSoon')">▶</button>
    </form>
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
</style>
