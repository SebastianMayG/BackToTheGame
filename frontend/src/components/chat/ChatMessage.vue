<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import type { CommentaryLine } from '@/api/types'

const props = defineProps<{ line: CommentaryLine }>()
const { t } = useI18n()

const icon = computed(() => ({ narrator: 'pi-microphone', pundit: 'pi-comment', system: 'pi-megaphone' })[props.line.speaker])

const box = computed(() => {
  const l = props.line
  return [
    l.level === 1 ? 'bg-raised' : '',
    l.speaker === 'pundit' ? 'bg-primary/10' : '',
    l.speaker === 'system' ? 'bg-primary/10' : '',
    l.level === 1 && l.emotion === 'excited' ? 'border-l-4 border-primary' : '',
    l.level === 1 && l.emotion === 'disappointed' ? 'border-l-4 border-danger' : '',
  ]
})
const text = computed(() => [
  props.line.level === 1 ? 'font-bold' : '',
  props.line.level === 3 ? 'text-sm text-muted' : '',
  props.line.speaker === 'pundit' ? 'italic' : '',
])
</script>

<template>
  <li class="grid animate-[slide-in_0.25s_ease-out] grid-cols-[4.6rem_1fr] gap-2 rounded-lg px-2.5 py-2" :class="box">
    <span class="pt-0.5 text-sm text-muted tabular-nums">{{ line.clock }}</span>
    <div class="min-w-0">
      <span class="flex items-center gap-1.5 text-xs text-muted">
        <i :class="['pi', icon]" aria-hidden="true" />
        {{ t(`chat.${line.speaker}`) }}
        <i v-if="line.favourite" class="pi pi-star-fill text-lime" :aria-label="t('fav.title')" />
        <Tag
          v-if="line.source === 'ai'"
          :value="t('chat.ai')"
          icon="pi pi-sparkles"
          severity="info"
          rounded
          class="!px-1.5 !py-0 !text-[0.65rem]"
        />
        <Tag v-else :value="t('chat.template')" severity="secondary" rounded class="!px-1.5 !py-0 !text-[0.65rem]" />
      </span>
      <p class="mb-0 mt-0.5 leading-snug" :class="text">{{ line.text }}</p>
    </div>
  </li>
</template>

<style>
@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
</style>
