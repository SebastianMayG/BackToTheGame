import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { Lang, Level, Mode } from '@/api/types'

const KEY = 'matchvoice.profile'

interface SavedProfile {
  lang: Lang
  mode: Mode
  club: string | null
  player: string | null
  intensity: Level
  voice: boolean
  names: boolean
  speed: number
  seed: number
  home: string
  away: string
  ai: boolean
}

const defaults: SavedProfile = {
  lang: 'es',
  mode: 'fan',
  club: null,
  player: null,
  intensity: 2,
  voice: true,
  names: false,
  speed: 30,
  seed: 42,
  home: 'NVR',
  away: 'KBY',
  ai: false, // the AI crew costs model calls, so it is opt-in
}

function load(): SavedProfile {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? { ...defaults, ...(JSON.parse(raw) as Partial<SavedProfile>) } : { ...defaults }
  } catch {
    return { ...defaults }
  }
}

/** Viewer personalisation, remembered in this browser only. */
export const useProfile = defineStore('profile', () => {
  const saved = load()
  const lang = ref<Lang>(saved.lang)
  const mode = ref<Mode>(saved.mode)
  const club = ref<string | null>(saved.club)
  const player = ref<string | null>(saved.player)
  const intensity = ref<Level>(saved.intensity)
  const voice = ref(saved.voice)
  const names = ref(saved.names)
  const speed = ref(saved.speed)
  const seed = ref(saved.seed)
  const home = ref(saved.home)
  const away = ref(saved.away)
  const ai = ref(saved.ai)

  watch(
    [lang, mode, club, player, intensity, voice, names, speed, seed, home, away, ai],
    () => {
      try {
        localStorage.setItem(
          KEY,
          JSON.stringify({
            lang: lang.value, mode: mode.value, club: club.value, player: player.value,
            intensity: intensity.value, voice: voice.value, names: names.value, speed: speed.value,
            seed: seed.value, home: home.value, away: away.value, ai: ai.value,
          } satisfies SavedProfile),
        )
      } catch {
        /* storage blocked: the profile still works for this session */
      }
    },
  )

  return { lang, mode, club, player, intensity, voice, names, speed, seed, home, away, ai }
})
