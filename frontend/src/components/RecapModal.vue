<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { useMatch } from '@/stores/match'

const { t } = useI18n()
const match = useMatch()

// The dialog handles focus trapping, Esc and the backdrop; closing it just clears the recap.
const visible = computed({
  get: () => match.recap !== null,
  set: (open: boolean) => {
    if (!open) match.recap = null
  },
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :draggable="false"
    :style="{ width: '36rem' }"
    :breakpoints="{ '640px': '94vw' }"
    aria-labelledby="recap-title"
  >
    <template #header>
      <div class="grid gap-1">
        <p class="m-0 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-primary">
          {{ match.recap ? t(`recap.${match.recap.kind}`) : '' }}
          <Tag v-if="match.recap?.source === 'ai'" :value="t('chat.ai')" icon="pi pi-sparkles" severity="info" rounded />
        </p>
        <h3 id="recap-title" class="m-0 font-display text-3xl font-bold uppercase tracking-wide">{{ match.recap?.headline }}</h3>
      </div>
    </template>

    <template v-if="match.recap">
      <p v-for="(para, i) in match.recap.text.split('\n')" :key="i" class="mb-3 mt-0 leading-relaxed">{{ para }}</p>
      <!-- the template text already ends with this line, so it is only added for AI recaps -->
      <p
        v-if="match.recap.player_of_the_match && match.recap.source === 'ai'"
        class="m-0 flex items-center gap-2 text-lime"
      >
        <i class="pi pi-trophy" aria-hidden="true" />
        {{ t('recap.pom') }}: <strong>{{ match.recap.player_of_the_match.name }}</strong>
      </p>
    </template>

    <template #footer>
      <Button :label="t('recap.close')" autofocus @click="visible = false" />
    </template>
  </Dialog>
</template>
