<script setup lang="ts">
import Card from 'primevue/card'

defineProps<{ title?: string; icon?: string }>()
</script>

<template>
  <Card
    :pt="{
      root: { class: 'flex min-h-0 flex-col !rounded-lg border border-line !shadow-none' },
      body: { class: 'flex min-h-0 flex-1 flex-col gap-2 !p-3.5' },
      title: { class: '!text-base' },
      content: { class: 'flex min-h-0 flex-1 flex-col' },
    }"
  >
    <template v-if="title" #title>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="panel-title !mb-0 flex items-center gap-2">
          <i v-if="icon" :class="['pi', icon]" aria-hidden="true" />{{ title }}
        </h2>
        <slot name="actions" />
      </div>
    </template>
    <template #content>
      <slot />
    </template>
  </Card>
</template>
