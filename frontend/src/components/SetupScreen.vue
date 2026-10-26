<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import Select from 'primevue/select'
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

const MODES: { id: Mode; icon: string }[] = [
  { id: 'fan', icon: 'pi-star' },
  { id: 'analyst', icon: 'pi-chart-bar' },
  { id: 'accessible', icon: 'pi-eye' },
]
const LANGS: { id: Lang; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'es', label: 'Español' },
]
const SPEEDS = [10, 20, 30, 60]

const matchClubs = computed(() => clubs.value.filter((c) => c.id === profile.home || c.id === profile.away))
const favClub = computed(() => clubs.value.find((c) => c.id === profile.club) ?? null)
const squad = computed(() =>
  (favClub.value?.squad ?? []).map((p) => ({ id: p.id, label: `#${p.number} ${p.name} · ${p.position}` })),
)
const speedOptions = computed(() =>
  SPEEDS.map((s) => ({ id: s, label: `x${s} · ${t('setup.speedHint', { min: Math.round(96 / s) })}` })),
)

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
  <main class="mx-auto max-w-5xl px-4 py-8">
    <div class="mb-5">
      <h1 class="m-0 flex items-center gap-3 text-4xl font-extrabold max-sm:text-3xl">
        <img class="size-[1em]" src="/soccer.svg" alt="" /> Back to the game
      </h1>
      <p class="mb-0 mt-1 text-muted">{{ t('app.tagline') }}</p>
    </div>

    <Card :pt="{ root: { class: '!rounded-xl border border-line !shadow-none' }, body: { class: '!p-5' } }">
      <template #title>
        <h2 class="m-0 text-xl font-semibold">{{ t('setup.title') }}</h2>
      </template>
      <template #content>
        <form class="grid gap-5" @submit.prevent="emit('start')">
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

          <fieldset class="m-0 border-0 p-0">
            <legend class="mb-1.5 p-0 text-sm text-muted">{{ t('setup.match') }}</legend>
            <div class="grid items-end gap-3 sm:grid-cols-[1fr_auto_1fr]">
              <label class="grid gap-1 text-sm text-muted">
                {{ t('setup.home') }}
                <Select
                  v-model="profile.home"
                  :options="clubs"
                  option-label="name"
                  option-value="id"
                  :option-disabled="(c: Club) => c.id === profile.away"
                  fluid
                />
              </label>
              <span class="pb-2 text-center text-muted max-sm:hidden">vs</span>
              <label class="grid gap-1 text-sm text-muted">
                {{ t('setup.away') }}
                <Select
                  v-model="profile.away"
                  :options="clubs"
                  option-label="name"
                  option-value="id"
                  :option-disabled="(c: Club) => c.id === profile.home"
                  fluid
                />
              </label>
            </div>
          </fieldset>

          <fieldset class="m-0 border-0 p-0">
            <legend class="mb-1.5 p-0 text-sm text-muted">{{ t('setup.mode') }}</legend>
            <div class="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
              <button
                v-for="m in MODES"
                :key="m.id"
                type="button"
                class="grid cursor-pointer gap-1 rounded-xl border bg-raised p-3 text-left text-inherit transition-colors hover:border-primary"
                :class="profile.mode === m.id ? 'border-primary ring-1 ring-primary' : 'border-line'"
                :aria-pressed="profile.mode === m.id"
                @click="profile.mode = m.id"
              >
                <strong class="flex items-center gap-2" :class="{ 'text-primary': profile.mode === m.id }">
                  <i :class="['pi', m.icon]" aria-hidden="true" />{{ t(`mode.${m.id}`) }}
                </strong>
                <small class="text-muted">{{ t(`modeHint.${m.id}`) }}</small>
              </button>
            </div>
          </fieldset>

          <div class="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
            <label class="grid gap-1 text-sm text-muted">
              {{ t('setup.lang') }}
              <Select v-model="profile.lang" :options="LANGS" option-label="label" option-value="id" fluid />
            </label>
            <label class="grid gap-1 text-sm text-muted">
              {{ t('setup.club') }}
              <Select
                v-model="profile.club"
                :options="matchClubs"
                option-label="name"
                option-value="id"
                :placeholder="t('setup.noClub')"
                show-clear
                fluid
              />
            </label>
            <label class="grid gap-1 text-sm text-muted">
              {{ t('setup.player') }}
              <Select
                v-model="profile.player"
                :options="squad"
                option-label="label"
                option-value="id"
                :placeholder="t('setup.noPlayer')"
                :disabled="!favClub"
                show-clear
                fluid
              />
            </label>
            <label class="grid gap-1 text-sm text-muted">
              {{ t('setup.speed') }}
              <Select v-model="profile.speed" :options="speedOptions" option-label="label" option-value="id" fluid />
            </label>
          </div>

          <Button type="submit" :label="t('setup.start')" icon="pi pi-play" icon-pos="right" class="justify-self-start" :disabled="!clubs.length" />
        </form>
      </template>
    </Card>
  </main>
</template>
