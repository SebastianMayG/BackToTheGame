import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import type { Intensity, Lang, Mode } from '@/api/types'

// v2: English is the default language, and the match and the narration level are no longer remembered.
const KEY = 'matchvoice.profile.v2'

interface SavedProfile {
  lang: Lang
  mode: Mode
  club: string | null
  player: string | null
  voice: boolean
  names: boolean
  speed: number
  home: string
  away: string
}

const defaults: SavedProfile = {
  lang: 'en',
  mode: 'fan',
  club: null,
  player: null,
  voice: true,
  names: false,
  speed: 30,
  home: 'NVR',
  away: 'KBY',
}

function load(): SavedProfile {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? { ...defaults, ...(JSON.parse(raw) as Partial<SavedProfile>) } : { ...defaults }
  } catch {
    return { ...defaults }
  }
}

/** A different match on every visit. Fixed with `?seed=` in the URL when a demo needs the same one. */
export const randomSeed = () => Math.floor(Math.random() * 100000)

/** Viewer personalisation, remembered in this browser only. */
export const useProfile = defineStore('profile', () => {
  const saved = load()
  const lang = ref<Lang>(saved.lang)
  const mode = ref<Mode>(saved.mode)
  const club = ref<string | null>(saved.club)
  const player = ref<string | null>(saved.player)
  const voice = ref(saved.voice)
  const names = ref(saved.names)
  const speed = ref(saved.speed)
  const home = ref(saved.home)
  const away = ref(saved.away)
  // Not saved: each visit starts on the big moments, with a new match and the AI crew on.
  const intensity = ref<Intensity>(1)
  const seed = ref(randomSeed())
  // `?ai=0` in the URL turns the AI crew off for that visit (testing, no spend).
  const ai = ref(true)

  watch(
    [lang, mode, club, player, voice, names, speed, home, away],
    () => {
      try {
        localStorage.setItem(
          KEY,
          JSON.stringify({
            lang: lang.value, mode: mode.value, club: club.value, player: player.value,
            voice: voice.value, names: names.value, speed: speed.value, home: home.value, away: away.value,
          } satisfies SavedProfile),
        )
      } catch {
        /* storage blocked: the profile still works for this session */
      }
    },
  )

  function newSeed() {
    seed.value = randomSeed()
  }

  return { lang, mode, club, player, intensity, voice, names, speed, seed, home, away, ai, newSeed }
})
