import { computed } from 'vue'
import type { Location, MatchEvent } from '@/api/types'
import { viewTransform } from '@/lib/pitch'
import { useMatch } from '@/stores/match'
import { useView } from '@/stores/view'

/** Events for the analyst layers, filtered by the panel's team/player and mapped to screen coordinates. */
export function useLayerEvents(types: MatchEvent['type'][]) {
  const match = useMatch()
  const view = useView()
  const transforms = computed(() => ({ 1: viewTransform(view.viewSide, 1), 2: viewTransform(view.viewSide, 2) }))

  const events = computed(() =>
    match.events.filter(
      (e) =>
        types.includes(e.type) &&
        e.location &&
        (view.layerTeam === 'both' || e.team === view.layerTeam) &&
        (!view.layerPlayer || e.player?.id === view.layerPlayer) &&
        (!view.layerPeriod || e.period === view.layerPeriod) &&
        (view.layerFrom === null || e.elapsed >= view.layerFrom * 60) &&
        (view.layerTo === null || e.elapsed <= view.layerTo * 60),
    ),
  )

  // Each event uses its own half's transform, so a team keeps its attacking direction on screen.
  const project = (e: MatchEvent, p: Location) => transforms.value[e.period](p)

  return { events, project }
}
