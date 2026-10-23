import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { OverlaySpec, Side } from '@/api/types'
import { useMatch } from './match'
import { useProfile } from './profile'

export type Layer = 'none' | 'shot_map' | 'heatmap' | 'progressive'

const LAYER_OF_SPEC: Record<OverlaySpec['layer'], Layer> = {
  shot_map: 'shot_map',
  heatmap: 'heatmap',
  progressive_passes: 'progressive',
}

/** What the pitch shows: analyst layers and filters, plus whose point of view we draw from. */
export const useView = defineStore('view', () => {
  const layer = ref<Layer>('none')
  const layerTeam = ref<Side | 'both'>('both')
  const layerPlayer = ref<string | null>(null)
  // Extra filters that only the Analyst Query agent sets.
  const layerPeriod = ref<1 | 2 | null>(null)
  const layerFrom = ref<number | null>(null) // minutes
  const layerTo = ref<number | null>(null)
  const overlay = ref<OverlaySpec | null>(null)
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

  function clearOverlay() {
    overlay.value = null
    layerPeriod.value = null
    layerFrom.value = null
    layerTo.value = null
  }

  /** Pick a layer by hand; this drops whatever the agent had set up. */
  function setLayer(l: Layer) {
    clearOverlay()
    layer.value = l
  }

  /** Draw what the Analyst Query agent asked for. */
  function applyOverlay(spec: OverlaySpec) {
    overlay.value = spec
    layer.value = LAYER_OF_SPEC[spec.layer]
    layerTeam.value = spec.filter.team ?? 'both'
    layerPlayer.value = spec.filter.player_id ?? null
    layerPeriod.value = spec.filter.period ?? null
    layerFrom.value = spec.filter.from_minute ?? null
    layerTo.value = spec.filter.to_minute ?? null
  }

  return {
    layer, layerTeam, layerPlayer, layerPeriod, layerFrom, layerTo, overlay, compareA, compareB,
    favSide, viewSide, clearOverlay, setLayer, applyOverlay,
  }
})
