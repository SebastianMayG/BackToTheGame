import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Side } from '@/api/types'
import { useMatch } from './match'
import { useProfile } from './profile'

export type Layer = 'none' | 'shot_map' | 'heatmap' | 'progressive'

/** What the pitch shows: analyst layers and filters, plus whose point of view we draw from. */
export const useView = defineStore('view', () => {
  const layer = ref<Layer>('none')
  const layerTeam = ref<Side | 'both'>('both')
  const layerPlayer = ref<string | null>(null)
  const compareA = ref<string | null>(null)
  const compareB = ref<string | null>(null)

  const match = useMatch()
  const profile = useProfile()

  /** The viewer's club side in this match, if they picked one of the two clubs. */
  const favSide = computed<Side | null>(() => {
    const m = match.meta
    if (!m || !profile.club) return null
    if (profile.club === m.home.id) return 'home'
    if (profile.club === m.away.id) return 'away'
    return null
  })
  /** The side drawn attacking left to right. */
  const viewSide = computed<Side>(() => favSide.value ?? 'home')

  return { layer, layerTeam, layerPlayer, compareA, compareB, favSide, viewSide }
})
