import { defineStore } from 'pinia'
import { computed, ref, shallowRef, triggerRef } from 'vue'
import { streamUrl, type StreamOptions } from '@/api/client'
import type {
  CommentaryLine,
  CrewStatus,
  Location,
  MatchEvent,
  MatchMeta,
  Moment,
  PlayerRef,
  Recap,
  Side,
  StatsSnapshot,
} from '@/api/types'
import type { Lineup } from '@/lib/pitch'

export type Status = 'idle' | 'connecting' | 'live' | 'ended' | 'error'

const STARTING_ROLES = ['GK', 'RB', 'RCB', 'LCB', 'LB', 'DM', 'RCM', 'LCM', 'RW', 'ST', 'LW']
const MAX_LINES = 400
const MAX_CREW = 120

type LineListener = (line: CommentaryLine) => void

function startingLineup(meta: MatchMeta, side: Side): Lineup {
  const club = side === 'home' ? meta.home : meta.away
  const lineup: Lineup = {}
  for (const p of club.squad) {
    if (STARTING_ROLES.includes(p.position)) {
      lineup[p.position] = { id: p.id, name: p.name, number: p.number, position: p.position }
    }
  }
  return lineup
}

/** Live match state, fed by the Server-Sent Events stream. */
export const useMatch = defineStore('match', () => {
  const status = ref<Status>('idle')
  const options = ref<StreamOptions | null>(null)
  const meta = ref<MatchMeta | null>(null)
  const events = shallowRef<MatchEvent[]>([])
  const last = ref<MatchEvent | null>(null)
  const lines = ref<CommentaryLine[]>([])
  const moments = ref<Moment[]>([])
  const stats = ref<StatsSnapshot | null>(null)
  const momentumHistory = ref<{ elapsed: number; value: number }[]>([])
  const recap = ref<Recap | null>(null)
  const crew = ref<CrewStatus[]>([]) // latest status per agent and moment, in arrival order
  const crewDisabled = ref('') // why the server did not start the AI crew, if it did not
  const lineups = ref<Record<Side, Lineup>>({ home: {}, away: {} })
  const ball = ref<Location>({ x: 52.5, y: 34 })
  const carrierId = ref<string | null>(null)
  const possession = ref<Side | null>(null)

  const period = computed<1 | 2>(() => (last.value?.period ?? 1) as 1 | 2)
  const elapsed = computed(() => last.value?.elapsed ?? 0)
  const clock = computed(() => last.value?.clock.display ?? '00:00')
  const score = computed(() => last.value?.score ?? { home: 0, away: 0 })

  let source: EventSource | null = null
  const listeners = new Set<LineListener>()

  function onLine(fn: LineListener): () => void {
    listeners.add(fn)
    return () => listeners.delete(fn)
  }

  function pushLine(line: CommentaryLine) {
    if (lines.value.some((l) => l.id === line.id)) return // a reconnect may resend the last event
    if (line.source === 'ai' && line.moment_id) {
      // The AI narrator line takes the place of the template analysis line for the same moment.
      const i = lines.value.findIndex(
        (l) => l.source === 'template' && l.speaker === 'pundit' && l.moment_id === line.moment_id && l.lang === line.lang,
      )
      if (i >= 0) lines.value.splice(i, 1)
    }
    // AI lines arrive a few seconds after the play: keep the chat in match order.
    let at = lines.value.length
    while (at > 0 && lines.value[at - 1].elapsed > line.elapsed) at--
    lines.value.splice(at, 0, line)
    if (lines.value.length > MAX_LINES) lines.value.splice(0, lines.value.length - MAX_LINES)
    for (const fn of listeners) fn(line)
  }

  function applyCrew(raw: CrewStatus | { agent: 'crew'; status: 'disabled'; reason: string }) {
    if (raw.agent === 'crew') {
      crewDisabled.value = raw.reason
      return
    }
    const i = crew.value.findIndex((c) => c.agent === raw.agent && c.moment_id === raw.moment_id)
    if (i >= 0) crew.value[i] = raw
    else crew.value.push(raw)
    if (crew.value.length > MAX_CREW) crew.value.splice(0, crew.value.length - MAX_CREW)
  }

  function applyEvent(ev: MatchEvent) {
    events.value.push(ev)
    triggerRef(events)
    last.value = ev
    possession.value = ev.possession.team ?? null
    const d = (ev.data ?? {}) as Record<string, any>
    if (ev.location) ball.value = ev.location
    if (ev.player && ev.team === ev.possession.team) carrierId.value = ev.player.id

    switch (ev.type) {
      case 'pass':
        if (d.outcome === 'complete') {
          ball.value = d.end_location
          carrierId.value = d.recipient?.id ?? null
        } else {
          ball.value = d.end_location
        }
        break
      case 'carry':
        ball.value = d.end_location
        break
      case 'substitution': {
        const side = ev.team as Side
        lineups.value[side][d.role] = d.player_in as PlayerRef
        break
      }
      case 'card':
        if (d.color === 'red' && ev.team && ev.player) {
          const lineup = lineups.value[ev.team]
          for (const [role, p] of Object.entries(lineup)) if (p.id === ev.player.id) delete lineup[role]
        }
        break
      case 'period_start':
      case 'kickoff':
        ball.value = { x: 52.5, y: 34 }
        break
    }
  }

  function reset() {
    events.value = []
    last.value = null
    lines.value = []
    moments.value = []
    stats.value = null
    momentumHistory.value = []
    recap.value = null
    crew.value = []
    crewDisabled.value = ''
    carrierId.value = null
    possession.value = null
    ball.value = { x: 52.5, y: 34 }
  }

  /** Start a match, or with `resume` switch language/mode/club mid-match and carry on from the last event. */
  function start(opts: StreamOptions, resume = false) {
    const fromSeq = resume ? (last.value?.seq ?? 0) : 0
    stop()
    if (!resume) reset()
    options.value = { ...opts, from_seq: undefined }
    status.value = 'connecting'
    const es = new EventSource(streamUrl({ ...opts, from_seq: fromSeq || undefined }))
    source = es
    const parse = <T>(e: MessageEvent): T => JSON.parse(e.data) as T

    es.addEventListener('open', () => {
      if (status.value !== 'ended') status.value = 'live'
    })
    es.addEventListener('meta', (e) => {
      const m = parse<MatchMeta>(e as MessageEvent)
      meta.value = m
      if (!resume) lineups.value = { home: startingLineup(m, 'home'), away: startingLineup(m, 'away') }
    })
    es.addEventListener('match_event', (e) => applyEvent(parse<MatchEvent>(e as MessageEvent)))
    es.addEventListener('pbp', (e) => pushLine(parse<CommentaryLine>(e as MessageEvent)))
    es.addEventListener('commentary', (e) => pushLine(parse<CommentaryLine>(e as MessageEvent)))
    es.addEventListener('moment', (e) => moments.value.push(parse<Moment>(e as MessageEvent)))
    es.addEventListener('crew_status', (e) => applyCrew(parse<Parameters<typeof applyCrew>[0]>(e as MessageEvent)))
    es.addEventListener('stats', (e) => {
      const s = parse<StatsSnapshot>(e as MessageEvent)
      stats.value = s
      momentumHistory.value.push({ elapsed: s.elapsed, value: s.momentum })
    })
    es.addEventListener('recap', (e) => (recap.value = parse<Recap>(e as MessageEvent)))
    es.addEventListener('end', () => {
      status.value = 'ended'
      es.close()
    })
    es.addEventListener('error', () => {
      // EventSource retries on its own with Last-Event-ID; the server resumes from there.
      if (status.value !== 'ended') status.value = es.readyState === EventSource.CLOSED ? 'error' : 'connecting'
    })
  }

  function stop() {
    source?.close()
    source = null
    if (status.value === 'live' || status.value === 'connecting') status.value = 'idle'
  }

  return {
    status, options, meta, events, last, lines, moments, stats, momentumHistory, recap, crew, crewDisabled, lineups,
    ball, carrierId, possession, period, elapsed, clock, score,
    start, stop, reset, onLine, pushLine,
  }
})
