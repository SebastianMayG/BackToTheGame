import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { CommentaryLine } from '@/api/types'
import { randomSeed } from '@/stores/profile'
import { useMatch } from './match'

const line = (over: Partial<CommentaryLine>): CommentaryLine => ({
  id: 'x',
  elapsed: 0,
  clock: '00:00',
  speaker: 'narrator',
  level: 1,
  lang: 'en',
  text: 'text',
  emotion: 'neutral',
  source: 'template',
  favourite: false,
  ...over,
})

describe('match store lines', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps the chat in match order when an AI line arrives late', () => {
    const m = useMatch()
    m.pushLine(line({ id: 'a', elapsed: 100 }))
    m.pushLine(line({ id: 'c', elapsed: 300 }))
    m.pushLine(line({ id: 'b', elapsed: 200, source: 'ai' }))
    expect(m.lines.map((l) => l.id)).toEqual(['a', 'b', 'c'])
  })

  it('replaces the template analysis line of a moment with the AI line', () => {
    const m = useMatch()
    m.pushLine(line({ id: 'tpl', speaker: 'pundit', moment_id: 'm1', elapsed: 100 }))
    m.pushLine(line({ id: 'ai', moment_id: 'm1', elapsed: 100, source: 'ai' }))
    expect(m.lines.map((l) => l.id)).toEqual(['ai'])
  })

  it('ignores a line it already has (a reconnect resends the last event)', () => {
    const m = useMatch()
    m.pushLine(line({ id: 'a' }))
    m.pushLine(line({ id: 'a' }))
    expect(m.lines).toHaveLength(1)
  })
})

describe('random seed', () => {
  it('is an integer the API accepts and changes between visits', () => {
    const seeds = new Set(Array.from({ length: 50 }, randomSeed))
    expect(seeds.size).toBeGreaterThan(40)
    for (const s of seeds) {
      expect(Number.isInteger(s)).toBe(true)
      expect(s).toBeGreaterThanOrEqual(0)
      expect(s).toBeLessThan(100000)
    }
  })
})
