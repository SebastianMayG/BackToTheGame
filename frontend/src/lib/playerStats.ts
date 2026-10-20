import type { MatchEvent } from '@/api/types'

export interface LivePlayerStats {
  touches: number
  passes: number
  passesCompleted: number
  shots: number
  xg: number
  goals: number
  sprints: number
  topSpeed: number
  carryDistance: number
  regains: number
}

const num = (v: unknown) => (typeof v === 'number' ? v : 0)

/** Live stats for any player, computed from the events seen so far (the Analyst snapshot only lists the top 5). */
export function playerStats(events: MatchEvent[], playerId: string | null): LivePlayerStats {
  const s: LivePlayerStats = {
    touches: 0, passes: 0, passesCompleted: 0, shots: 0, xg: 0, goals: 0,
    sprints: 0, topSpeed: 0, carryDistance: 0, regains: 0,
  }
  if (!playerId) return s
  for (const ev of events) {
    if (ev.player?.id !== playerId) continue
    const d = ev.data ?? {}
    switch (ev.type) {
      case 'pass':
        s.touches++
        s.passes++
        if (d.outcome === 'complete') s.passesCompleted++
        break
      case 'carry':
        s.touches++
        s.carryDistance += num(d.distance)
        s.topSpeed = Math.max(s.topSpeed, num(d.top_speed_kmh))
        if (d.sprint) s.sprints++
        break
      case 'shot':
        s.touches++
        s.shots++
        s.xg += num(d.xg)
        break
      case 'goal':
        s.goals++
        break
      case 'tackle':
        if (d.outcome === 'won') s.regains++
        break
      case 'interception':
        s.regains++
        break
    }
  }
  s.xg = Math.round(s.xg * 100) / 100
  s.carryDistance = Math.round(s.carryDistance)
  return s
}
