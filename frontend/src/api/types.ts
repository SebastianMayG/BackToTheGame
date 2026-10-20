// Friendly aliases over the types generated from the FastAPI OpenAPI schema (npm run gen:types).
// The Python Pydantic models are the single source of truth.
import type { components } from './types.gen'

type S = components['schemas']

export type Club = S['Club']
export type Player = S['Player']
export type PlayerRef = S['PlayerRef']
export type MatchMeta = S['MatchMeta']
export type MatchEvent = S['MatchEvent']
export type Moment = S['Moment']
export type StatsSnapshot = S['StatsSnapshot']
export type TeamStats = S['TeamStats']
export type PlayerStats = S['PlayerStats']
export type CommentaryLine = S['CommentaryLine']
export type Recap = S['Recap']
export type Location = S['Location']

export type Side = 'home' | 'away'
export type Lang = 'es' | 'en'
export type Mode = 'fan' | 'analyst' | 'accessible'
export type Level = 1 | 2 | 3
