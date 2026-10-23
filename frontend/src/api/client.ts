import type { Club, Lang, Mode, Recap } from './types'

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
): Promise<Recap> {
  const q = query({ home: setup.home, away: setup.away, until, since, lang, club })
  return getJson<Recap>(`/api/matches/${setup.seed}/catchup?${q}`)
}

export function exportUrl(setup: MatchSetup, format: 'csv' | 'json'): string {
  return `/api/matches/${setup.seed}/export?${query({ home: setup.home, away: setup.away, format })}`
}
