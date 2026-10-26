<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import SelectButton from 'primevue/selectbutton'
import type { Intensity, Level } from '@/api/types'
import AppPanel from '@/components/AppPanel.vue'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import AskBox from './AskBox.vue'
import ChatMessage from './ChatMessage.vue'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()

const LEVELS: Intensity[] = [1, 2]
const levelOptions = computed(() => LEVELS.map((l) => ({ value: l, label: t(`intensity.${l}`) })))

// Accessible mode always describes the build-up as well.
const maxLevel = computed<Level>(() => (profile.mode === 'accessible' ? 2 : profile.intensity))
const visible = computed(() => match.lines.filter((l) => l.lang === profile.lang && l.level <= maxLevel.value).slice(-150))

const list = ref<HTMLElement | null>(null)
const pinned = ref(true) // follow the newest line unless the viewer scrolls up

function onScroll() {
  const el = list.value
  if (el) pinned.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}

watch(
  () => visible.value.length,
  async () => {
    if (!pinned.value) return
    await nextTick()
    list.value?.scrollTo({ top: list.value.scrollHeight })
  },
)
</script>

<template>
  <AppPanel :title="t('chat.title')" icon="pi-microphone" class="h-full">
    <template #actions>
      <SelectButton
        v-model="profile.intensity"
        :options="levelOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        size="small"
        :aria-label="t('controls.intensity')"
      />
    </template>

    <ol
      ref="list"
      class="m-0 flex min-h-60 flex-1 list-none flex-col gap-1 overflow-y-auto p-0"
      aria-live="polite"
      aria-relevant="additions"
      @scroll="onScroll"
    >
      <li v-if="!visible.length" class="px-2 py-5 text-muted">{{ t('chat.empty') }}</li>
      <ChatMessage v-for="line in visible" :key="line.id" :line="line" />
    </ol>
    <AskBox />
  </AppPanel>
</template>
