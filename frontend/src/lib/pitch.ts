import type { Location, PlayerRef, Side } from '@/api/types'

export const PITCH_L = 105
export const PITCH_W = 68

export type Lineup = Record<string, PlayerRef> // match role -> player

export interface PlacedPlayer {
  player: PlayerRef
  side: Side
  role: string
  x: number
  y: number
  onBall: boolean
}

// 4-3-3 base positions in the team's attacking frame (x toward the opponent goal, low y = right flank).
const BASE: Record<string, [number, number]> = {
  GK: [5, 34],
  RB: [30, 10],
  RCB: [24, 25],
  LCB: [24, 43],
  LB: [30, 58],
  DM: [38, 34],
  RCM: [48, 22],
  LCM: [48, 46],
  RW: [64, 9],
  ST: [68, 34],
  LW: [64, 59],
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

export function attacksRight(side: Side, period: 1 | 2): boolean {
  return (side === 'home') === (period === 1)
}

/** Absolute <-> attacking frame (the transform is its own inverse). */
export function toFrame(side: Side, period: 1 | 2, p: Location): Location {
  return attacksRight(side, period) ? { x: p.x, y: p.y } : { x: PITCH_L - p.x, y: PITCH_W - p.y }
}

/**
 * Simulated positions for all players. The generator only tracks the ball, so each team's block
 * slides with it: the team in possession pushes up and spreads, the defending team drops and narrows,
 * and the nearest defender steps out to press.
 */
export function teamShape(
  lineups: Record<Side, Lineup>,
  ball: Location,
  possession: Side | null,
  period: 1 | 2,
  carrierId: string | null,
): PlacedPlayer[] {
  const out: PlacedPlayer[] = []
  for (const side of ['home', 'away'] as Side[]) {
    const b = toFrame(side, period, ball)
    const inPoss = possession === side
    const shift = (b.x - 52.5) * 0.55 + (inPoss ? 6 : -4)
    const width = inPoss ? 1.12 : 0.72
    const slide = (b.y - 34) * (inPoss ? 0.2 : 0.42)
    const placed: PlacedPlayer[] = []
    for (const [role, player] of Object.entries(lineups[side])) {
      const [bx, by] = BASE[role] ?? [50, 34]
      let x: number
      let y: number
      if (role === 'GK') {
        x = clamp(bx + shift * 0.15, 2, 18)
        y = clamp(34 + (b.y - 34) * 0.15, 28, 40)
      } else {
        x = clamp(bx + shift, 3, 101)
        y = clamp(34 + (by - 34) * width + slide, 2, 66)
      }
      placed.push({ player, side, role, x, y, onBall: false })
    }
    if (inPoss && carrierId) {
      const c = placed.find((p) => p.player.id === carrierId)
      if (c) Object.assign(c, { x: b.x, y: b.y, onBall: true })
    } else if (!inPoss && possession) {
      // nearest outfield defender presses the ball
      let best: PlacedPlayer | null = null
      let bestD = Infinity
      for (const p of placed) {
        if (p.role === 'GK') continue
        const d = Math.hypot(p.x - b.x, p.y - b.y)
        if (d < bestD) [best, bestD] = [p, d]
      }
      if (best && bestD > 2.5) {
        const k = (bestD - 2.5) / bestD
        best.x -= (best.x - b.x) * k
        best.y -= (best.y - b.y) * k
      }
    }
    for (const p of placed) {
      const abs = toFrame(side, period, { x: p.x, y: p.y })
      out.push({ ...p, x: abs.x, y: abs.y })
    }
  }
  return out
}

/** Screen transform so the viewer's team always attacks left to right. */
export function viewTransform(viewSide: Side, period: 1 | 2): (p: Location) => Location {
  const flip = !attacksRight(viewSide, period)
  return (p) => (flip ? { x: PITCH_L - p.x, y: PITCH_W - p.y } : p)
}
