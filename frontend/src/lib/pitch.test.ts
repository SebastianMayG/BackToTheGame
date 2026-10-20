import { describe, expect, it } from 'vitest'
import type { PlayerRef } from '@/api/types'
import { attacksRight, teamShape, toFrame, viewTransform, type Lineup } from './pitch'

const ROLES = ['GK', 'RB', 'RCB', 'LCB', 'LB', 'DM', 'RCM', 'LCM', 'RW', 'ST', 'LW']
const lineup = (prefix: string): Lineup =>
  Object.fromEntries(
    ROLES.map((role, i) => [role, { id: `${prefix}-${i}`, name: `P${i}`, number: i + 1, position: role } as PlayerRef]),
  )

describe('pitch geometry', () => {
  it('home attacks right in the first half only', () => {
    expect(attacksRight('home', 1)).toBe(true)
    expect(attacksRight('home', 2)).toBe(false)
    expect(attacksRight('away', 2)).toBe(true)
  })

  it('frame transform is its own inverse', () => {
    const p = { x: 20, y: 10 }
    expect(toFrame('away', 1, toFrame('away', 1, p))).toEqual(p)
  })

  it('places 22 players inside the pitch, carrier on the ball', () => {
    const ball = { x: 70, y: 20 }
    const placed = teamShape({ home: lineup('H'), away: lineup('A') }, ball, 'home', 1, 'H-9')
    expect(placed).toHaveLength(22)
    for (const p of placed) {
      expect(p.x).toBeGreaterThanOrEqual(0)
      expect(p.x).toBeLessThanOrEqual(105)
      expect(p.y).toBeGreaterThanOrEqual(0)
      expect(p.y).toBeLessThanOrEqual(68)
    }
    const carrier = placed.find((p) => p.onBall)!
    expect(carrier.player.id).toBe('H-9')
    expect(carrier.x).toBeCloseTo(70)
  })

  it('goalkeepers stay near their own goal', () => {
    const placed = teamShape({ home: lineup('H'), away: lineup('A') }, { x: 52, y: 34 }, 'home', 1, null)
    expect(placed.find((p) => p.player.id === 'H-0')!.x).toBeLessThan(20)
    expect(placed.find((p) => p.player.id === 'A-0')!.x).toBeGreaterThan(85)
  })

  it('view transform keeps the viewer attacking left to right', () => {
    const t = viewTransform('away', 1) // away attacks toward x = 0 in period 1, so we flip
    expect(t({ x: 10, y: 5 })).toEqual({ x: 95, y: 63 })
    expect(viewTransform('home', 1)({ x: 10, y: 5 })).toEqual({ x: 10, y: 5 })
  })
})
