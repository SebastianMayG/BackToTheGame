<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMatch } from '@/stores/match'

const { t } = useI18n()
const match = useMatch()
const closeBtn = ref<HTMLButtonElement | null>(null)

watch(
  () => match.recap,
  async (r) => {
    if (r) {
      await nextTick()
      closeBtn.value?.focus()
    }
  },
)
const close = () => (match.recap = null)
</script>

<template>
  <div v-if="match.recap" class="backdrop" @click.self="close" @keydown.esc="close">
    <div class="modal panel" role="dialog" aria-modal="true" aria-labelledby="recap-title">
      <p class="kind">{{ t(`recap.${match.recap.kind}`) }}</p>
      <h3 id="recap-title">{{ match.recap.headline }}</h3>
      <p v-for="(para, i) in match.recap.text.split('\n')" :key="i">{{ para }}</p>
      <p v-if="match.recap.player_of_the_match" class="pom">
        🏅 {{ t('recap.pom') }}: <strong>{{ match.recap.player_of_the_match.name }}</strong>
      </p>
      <button ref="closeBtn" class="primary" @click="close">{{ t('recap.close') }}</button>
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 10;
}
.modal {
  max-width: 560px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
}
.kind {
  margin: 0;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  font-weight: 700;
}
h3 {
  margin: 6px 0 10px;
  font-size: 1.5rem;
}
p {
  line-height: 1.45;
}
.pom {
  color: var(--accent-2);
}
</style>
