import type { AskResponse, Club, Lang, Mode, QueryResponse, Recap } from './types'

export interface MatchSetup {
  seed: number
  home: string
  away: string
}

export interface StreamOptions extends MatchSetup {
  speed: number
  lang: Lang
  mode: Mode
  club: string | null
  player: string | null
  ai?: boolean
  from_seq?: number
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${url}`)
  return (await res.json()) as T
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') q.set(k, String(v))
  }
  return q.toString()
}

export async function fetchClubs(): Promise<Club[]> {
  return (await getJson<{ clubs: Club[] }>('/api/clubs')).clubs
}

export function streamUrl(o: StreamOptions): string {
  const { seed, ...rest } = o
  return `/api/matches/${seed}/stream?${query({ ...rest })}`
}

export function fetchCatchup(
  setup: MatchSetup,
  until: number,
  since: number,
  lang: Lang,
  club: string | null,
  ai = false,
): Promise<Recap> {
  const q = query({ home: setup.home, away: setup.away, until, since, lang, club, ai })
  return getJson<Recap>(`/api/matches/${setup.seed}/catchup?${q}`)
}

export class AgentError extends Error {
  constructor(readonly status: number) {
    super(`agent returned ${status}`)
  }
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!res.ok) throw new AgentError(res.status)
  return (await res.json()) as T
}

/** Chat Q&A: the agent answers from the match data up to `untilMinute`. */
export function askMatch(setup: MatchSetup, question: string, untilMinute: number, lang: Lang, club: string | null) {
  return postJson<AskResponse>(`/api/matches/${setup.seed}/ask`, {
    question, until_minute: untilMinute, lang, home: setup.home, away: setup.away, club,
  })
}

/** Analyst Query: natural language in, a pitch layer (OverlaySpec) out. */
export function queryMatch(setup: MatchSetup, request: string, untilMinute: number, lang: Lang) {
  return postJson<QueryResponse>(`/api/matches/${setup.seed}/query`, {
    query: request, until_minute: untilMinute, lang, home: setup.home, away: setup.away,
  })
}

export function exportUrl(setup: MatchSetup, format: 'csv' | 'json'): string {
  return `/api/matches/${setup.seed}/export?${query({ home: setup.home, away: setup.away, format })}`
}
