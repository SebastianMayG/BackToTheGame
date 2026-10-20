# BackToTheGame

**Live, explainable and personalised match narration from synthetic football events.**
Built for the Microsoft + Premier League *Inside the Game* Developer Hackathon (2026).

The pitch is on the left and a live narration chat is on the right. Two commentators (play-by-play and pundit) tell the story of the match, with voice. Every viewer gets their own version of the same match: a fan who follows a club and a favourite player, a data-hungry analyst, or a blind or low-vision viewer who listens to a descriptive broadcast.

> **Status (work in progress):**
> - ✅ Synthetic match generator, Analyst engine, template narration in ES and EN, live SSE stream, Vue studio UI, browser voice, analyst layers, CI and Docker.
> - 🔜 Microsoft Foundry agents orchestrated with Microsoft Agent Framework, Azure AI Speech neural voices, MCP tools, Azure Container Apps deployment.

## Pipeline

```
Ingest            Interpret               Explain                Render                     Personalize
synthetic   ->    Analyst engine     ->   key moments with  ->   pitch + overlays +     ->  fan / analyst / accessible,
events (SSE)      (live stats, xG,        evidence (+ AI         narration chat + voice      club, player, language
                  PPDA, momentum)         agents, next)
```

| Stage | What runs today |
|---|---|
| **Ingest** | `engine/generator.py` produces a full match (about 2,300 events). The API replays it live as Server-Sent Events at any speed and resumes with `Last-Event-ID` |
| **Interpret** | `engine/analyst.py` keeps team and player stats live: possession, xG, shots, pass accuracy, progressive passes, box entries, PPDA, field tilt and player ratings |
| **Explain** | The Analyst flags key moments with their evidence: goal with context (opener, equaliser, against the run of play, brace), big chance, great save, momentum swing, control vs chaos, pressing spell, xG vs score, cards, rocket shots, sprints |
| **Render** | Vue 3 studio: SVG pitch with 22 players and the ball, speed and shot tags, a broadcast lower third, a momentum chart, a timeline and the narration chat |
| **Personalize** | **Fan:** your club always attacks left to right, rivals are dimmed, the commentary celebrates your goals, and your player has a halo and a live card. **Analyst:** shot map, heatmap, progressive pass layers, player comparison, CSV and JSON export. **Accessible:** descriptive narration ("in the final third, on the right"), voice at a higher level of detail, high contrast and larger text. ES and EN |

## Quick start

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/) and Node.js 22.

```bash
# backend (API on :4000)
cd backend
uv sync
uv run uvicorn matchvoice.main:app --reload --port 4000

# frontend (dev server on :5173, proxies /api to :4000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Shareable demo links work too, for example
`/?autostart=1&mode=analyst&club=NVR&player=NVR-9&lang=en&layer=shot_map`.

### Useful commands

```bash
cd backend
uv run pytest                                  # backend tests
uv run matchvoice calibrate --n 100            # realism check vs real football
uv run matchvoice analyse --seed 42            # key moments the Analyst finds
uv run matchvoice narrate --seed 42 --lang en  # template play-by-play
uv run matchvoice generate --seed 42           # write data/match-*.json

cd frontend
npm test                # unit tests (pitch geometry, team shape)
npm run gen:types       # regenerate TS types from the FastAPI OpenAPI schema (backend running)
npm run build
```

### Docker

```bash
docker build -t matchvoice .
docker run -p 8000:8000 matchvoice    # http://localhost:8000
```

## Synthetic data

There are four fictional clubs (Northvale Rovers, Kestrel Bay, Silverlake Athletic and Corran City), each with its own pressing, directness, quality and width. Each club has a fixed 16-player squad, so a favourite player stays the same across matches. Matches are fully repeatable from their seed.

The generator simulates possession chains: pressure, tackles, interceptions, passes with distance, progression and difficulty, carries and sprints, shots with an xG model and shot speed, saves, blocks, corners, free kicks, penalties, fouls, cards, substitutions and stoppage time. A hidden momentum value changes how teams play. It is never written to the events, so detecting it is the Analyst's job.

Realism check over 60 matches (per team, per match):

| Metric | Generator | Real top flight (approx.) |
|---|---|---|
| Goals | 1.2 | 1.4 |
| Shots | 13.7 | 12 to 13 |
| On target | 4.5 | 4 to 5 |
| Passes | 523 | 450 to 550 |
| Pass accuracy | 79% | 80 to 85% |
| Corners | 5.3 | 5 |
| Fouls | 12.6 | 10 to 11 |
| Yellow cards | 1.7 | 1.8 |

The event format is described in [docs/SCHEMA.md](docs/SCHEMA.md).

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/clubs` | Fictional clubs and squads |
| `GET /api/matches/{seed}?home=&away=` | Full match (meta and events) |
| `GET /api/matches/{seed}/stream?speed=&lang=&mode=&club=&player=&from_seq=` | Live SSE: `meta`, `match_event`, `pbp`, `moment`, `commentary`, `stats`, `recap`, `end` |
| `GET /api/matches/{seed}/analysis` | All key moments, final stats and player stats |
| `GET /api/matches/{seed}/catchup?until=&since=&lang=&club=` | "What did I miss?" recap |
| `GET /api/matches/{seed}/export?format=csv\|json` | Export for analysts |
| `GET /api/stream/contract` | A real sample of every stream payload (documents the SSE contract in OpenAPI) |
| `GET /docs` | Interactive OpenAPI docs |

## Architecture

```
backend/   Python 3.12 · FastAPI · Pydantic (single source of truth for the data contracts)
  src/matchvoice/
    models.py         data contracts (exported to TypeScript through OpenAPI)
    engine/           generator, analyst, narration templates, recaps (no AI: instant and exact)
    api/              REST + SSE
    agents/           (next) Microsoft Foundry agents
    orchestrator/     (next) Microsoft Agent Framework workflow: handoffs, shared state, guardrails, fallback
    mcp_server/       (next) MCP tools over the live match state
frontend/  Vue 3 · TypeScript · Vite · Pinia · vue-i18n
  src/components/     pitch (+ analyst layers), chat, score bar, stats, momentum, analyst panel, recap
  src/stores/         profile (personalisation), match (SSE state), view (layers)
  src/lib/            team-shape model and live player stats (unit tested)
```

**Design rule: code for the numbers, AI for the words.** Stats always come from the deterministic engine. Template lines arrive instantly for every event, so the chat and the voice never wait. The AI agents (next) will enrich the big moments and must only use numbers present in the Analyst's evidence. The templates remain the fallback.

## Data and IP

All clubs, players and matches are fictional and generated. No real match footage, league data, club names or marks are used.
