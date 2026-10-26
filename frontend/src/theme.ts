import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

// Matchday-programme look: warm paper, ink text, deep pitch green. Flat surfaces, thin borders, small radii,
// no glow and no gradients. The scales mirror the app palette in styles.css (page #f4f1ea, panel #fffdf8).
const pitchGreen = {
  50: '#eef6f1',
  100: '#d6eadd',
  200: '#aed5bc',
  300: '#80b997',
  400: '#4f9a70',
  500: '#1f6b45',
  600: '#19583a',
  700: '#144730',
  800: '#0f3724',
  900: '#0b281a',
  950: '#061a10',
}

const paper = {
  0: '#fffdf8',
  50: '#f7f4ed',
  100: '#f0ece2',
  200: '#ddd6c8',
  300: '#c9c0ae',
  400: '#9a9282',
  500: '#6b6558',
  600: '#3c3f48',
  700: '#1b1f2a',
  800: '#14171f',
  900: '#0e1015',
  950: '#07080b',
}

export const preset = definePreset(Aura, {
  // Info tags and messages would be blue; keep them in the pitch green so the page has no off-palette colour.
  primitive: { blue: pitchGreen, sky: pitchGreen },
  semantic: {
    primary: pitchGreen,
    borderRadius: { none: '0', xs: '2px', sm: '4px', md: '6px', lg: '8px', xl: '10px' },
    colorScheme: {
      light: {
        surface: paper,
        primary: {
          color: '{primary.500}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.600}',
          activeColor: '{primary.700}',
        },
      },
      // Only Accessible mode is dark (black and yellow); styles.css overrides the tokens that matter there.
      dark: {
        surface: { 0: '#ffffff', 50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa', 500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b', 950: '#000000' },
      },
    },
  },
})
