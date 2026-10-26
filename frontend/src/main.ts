import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import '@fontsource-variable/source-sans-3'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import 'primeicons/primeicons.css'
import App from './App.vue'
import { i18n } from './i18n'
import { preset } from './theme'
import './styles.css'

createApp(App)
  .use(createPinia())
  .use(i18n)
  .use(PrimeVue, {
    theme: {
      preset,
      options: {
        darkModeSelector: '.app-dark', // light by default; Accessible mode adds the class (black and yellow)
        // PrimeVue styles live in their own layer, below Tailwind's utilities, so a class like `p-4` always wins.
        cssLayer: { name: 'primevue', order: 'theme, base, primevue' },
      },
    },
  })
  .directive('tooltip', Tooltip)
  .mount('#app')
