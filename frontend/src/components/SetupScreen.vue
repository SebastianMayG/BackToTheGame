<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchClubs } from '@/api/client'
import type { Club, Lang, Mode } from '@/api/types'
import { useProfile } from '@/stores/profile'

const emit = defineEmits<{ start: [] }>()
const { t } = useI18n()
const profile = useProfile()
const clubs = ref<Club[]>([])
const error = ref('')

onMounted(async () => {
  try {
    clubs.value = await fetchClubs()
  } catch (e) {
    error.value = String(e)
  }
})

const MODES: Mode[] = ['fan', 'analyst', 'accessible']
const LANGS: { id: Lang; label: string }[] = [
  { id: 'es', label: 'Español' },
  { id: 'en', label: 'English' },
]
const SPEEDS = [10, 20, 30, 60]

const matchClubs = computed(() => clubs.value.filter((c) => c.id === profile.home || c.id === profile.away))
const favClub = computed(() => clubs.value.find((c) => c.id === profile.club) ?? null)
const squad = computed(() => favClub.value?.squad ?? [])

// keep the selections consistent
watch(
  () => [profile.home, profile.away],
  () => {
    if (profile.home === profile.away) {
      profile.away = clubs.value.find((c) => c.id !== profile.home)?.id ?? profile.away
    }
    if (profile.club && profile.club !== profile.home && profile.club !== profile.away) profile.club = null
  },
)
watch(
  () => profile.club,
  () => {
    if (profile.player && !squad.value.some((p) => p.id === profile.player)) profile.player = null
  },
)
</script>

<template>
  <main class="setup">
    <div class="hero">
      <h1><img class="logo" src="/soccer.svg" alt="" /> Back to the game</h1>
      <p class="muted">{{ t('app.tagline') }}</p>
    </div>

    <form class="panel form" @submit.prevent="emit('start')">
      <h2>{{ t('setup.title') }}</h2>
      <p v-if="error" class="error">{{ error }}</p>

      <fieldset>
        <legend>{{ t('setup.match') }}</legend>
        <div class="row">
          <label>
            {{ t('setup.home') }}
            <select v-model="profile.home">
              <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </label>
          <span class="vs">vs</span>
          <label>
            {{ t('setup.away') }}
            <select v-model="profile.away">
              <option v-for="c in clubs" :key="c.id" :value="c.id" :disabled="c.id === profile.home">{{ c.name }}</option>
            </select>
          </label>
          <label class="seed">
            {{ t('setup.seed') }}
            <input v-model.number="profile.seed" type="number" min="0" max="99999" />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>{{ t('setup.mode') }}</legend>
        <div class="modes">
          <button
            v-for="m in MODES"
            :key="m"
            type="button"
            class="mode"
            :class="{ active: profile.mode === m }"
            :aria-pressed="profile.mode === m"
            @click="profile.mode = m"
          >
            <strong>{{ t(`mode.${m}`) }}</strong>
            <small>{{ t(`modeHint.${m}`) }}</small>
          </button>
        </div>
      </fieldset>

      <div class="row">
        <label>
          {{ t('setup.lang') }}
          <select v-model="profile.lang">
            <option v-for="l in LANGS" :key="l.id" :value="l.id">{{ l.label }}</option>
          </select>
        </label>
        <label>
          {{ t('setup.club') }}
          <select v-model="profile.club">
            <option :value="null">{{ t('setup.noClub') }}</option>
            <option v-for="c in matchClubs" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label>
          {{ t('setup.player') }}
          <select v-model="profile.player" :disabled="!favClub">
            <option :value="null">{{ t('setup.noPlayer') }}</option>
            <option v-for="p in squad" :key="p.id" :value="p.id">#{{ p.number }} {{ p.name }} · {{ p.position }}</option>
          </select>
        </label>
        <label>
          {{ t('setup.speed') }}
          <select v-model.number="profile.speed">
            <option v-for="s in SPEEDS" :key="s" :value="s">x{{ s }} · {{ t('setup.speedHint', { min: Math.round(96 / s) }) }}</option>
          </select>
        </label>
      </div>

      <button type="submit" class="primary start" :disabled="!clubs.length">{{ t('setup.start') }} ▶</button>
    </form>
  </main>
</template>

<style scoped>
.setup {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 16px;
}
.hero h1 {
  margin: 0;
  font-size: 2.4rem;
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo {
  height: 1em;
  width: 1em;
}
.hero p {
  margin: 4px 0 20px;
}
.form {
  display: grid;
  gap: 16px;
}
fieldset {
  border: 0;
  padding: 0;
  margin: 0;
}
legend {
  font-size: 0.8rem;
  color: var(--muted);
  margin-bottom: 6px;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}
label {
  display: grid;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--muted);
  min-width: 160px;
  flex: 1;
}
label select,
label input {
  color: var(--text);
}
.seed {
  max-width: 160px;
}
.vs {
  padding-bottom: 8px;
  color: var(--muted);
}
.modes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}
.mode {
  text-align: left;
  display: grid;
  gap: 4px;
  padding: 12px;
}
.mode small {
  color: var(--muted);
}
.start {
  justify-self: start;
  padding: 10px 22px;
  font-size: 1.05rem;
}
.error {
  color: var(--danger);
}
</style>
