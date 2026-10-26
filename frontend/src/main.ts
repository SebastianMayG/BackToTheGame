import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
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
        darkModeSelector: '.app-dark', // the app is always dark; the class is set in index.html
        // PrimeVue styles live in their own layer, below Tailwind's utilities, so a class like `p-4` always wins.
        cssLayer: { name: 'primevue', order: 'theme, base, primevue' },
      },
    },
  })
  .directive('tooltip', Tooltip)
  .mount('#app')
