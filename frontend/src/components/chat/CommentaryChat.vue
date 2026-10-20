<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Level } from '@/api/types'
import { useMatch } from '@/stores/match'
import { useProfile } from '@/stores/profile'
import AskBox from './AskBox.vue'
import ChatMessage from './ChatMessage.vue'

const { t } = useI18n()
const match = useMatch()
const profile = useProfile()

// Accessible mode always describes the build-up as well.
const maxLevel = computed<Level>(() => (profile.mode === 'accessible' ? (Math.max(2, profile.intensity) as Level) : profile.intensity))
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
  <section class="chat panel" :aria-label="t('chat.title')">
    <header>
      <h2>🎙️ {{ t('chat.title') }}</h2>
      <div class="levels" role="group" :aria-label="t('controls.intensity')">
        <button
          v-for="lvl in [1, 2, 3] as Level[]"
          :key="lvl"
          :class="{ active: profile.intensity === lvl }"
          :aria-pressed="profile.intensity === lvl"
          @click="profile.intensity = lvl"
        >
          {{ t(`intensity.${lvl}`) }}
        </button>
      </div>
    </header>
    <ol ref="list" class="lines" aria-live="polite" aria-relevant="additions" @scroll="onScroll">
      <li v-if="!visible.length" class="empty muted">{{ t('chat.empty') }}</li>
      <ChatMessage v-for="line in visible" :key="line.id" :line="line" />
    </ol>
    <AskBox />
  </section>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}
header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
  align-items: center;
}
header h2 {
  margin: 0;
}
.levels {
  display: flex;
  gap: 4px;
}
.levels button {
  font-size: 0.72rem;
  padding: 3px 8px;
}
.lines {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 240px;
}
.empty {
  padding: 20px 8px;
}
</style>
