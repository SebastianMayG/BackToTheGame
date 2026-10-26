import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

// Broadcast look: deep navy surfaces with a cyan accent. The scale mirrors the palette the app already had
// (page #0b1020, panel #131a2e, raised #1a2340, line #26314f), so the pitch and charts keep matching.
const cyan = {
  50: '#ecfeff',
  100: '#cffafe',
  200: '#a5f3fc',
  300: '#67e8f9',
  400: '#22d3ee',
  500: '#06b6d4',
  600: '#0891b2',
  700: '#0e7490',
  800: '#155e75',
  900: '#164e63',
  950: '#083344',
}

const navy = {
  0: '#ffffff',
  50: '#eef1f8',
  100: '#e1e6f2',
  200: '#cdd4e6',
  300: '#b3bdd6',
  400: '#94a0bf',
  500: '#55638a',
  600: '#364469',
  700: '#26314f',
  800: '#1a2340',
  900: '#131a2e',
  950: '#0b1020',
}

export const preset = definePreset(Aura, {
  semantic: {
    primary: cyan,
    colorScheme: {
      dark: {
        surface: navy,
        primary: {
          color: '{primary.400}',
          contrastColor: '#04121a',
          hoverColor: '{primary.300}',
          activeColor: '{primary.200}',
        },
        highlight: {
          background: 'color-mix(in srgb, {primary.400}, transparent 84%)',
          focusBackground: 'color-mix(in srgb, {primary.400}, transparent 76%)',
          color: 'rgba(255,255,255,.87)',
          focusColor: 'rgba(255,255,255,.87)',
        },
      },
    },
  },
})
