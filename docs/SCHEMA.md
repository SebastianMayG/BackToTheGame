# Match event schema (v0.1)

The Pydantic models in [`backend/src/matchvoice/models.py`](../backend/src/matchvoice/models.py) are the source of truth. The frontend types are generated from them (`npm run gen:types`).

A match is `{ meta, events }`. Events are ordered by `seq`, with no gaps, and never go back in time.

## Coordinates

- The pitch is 105 m long (`x`) and 68 m wide (`y`). Coordinates are **absolute**.
- Home attacks toward `x = 105` in period 1 and toward `x = 0` in period 2. Away does the opposite.

## Common fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | `{match_id}-{seq}` |
| `seq` | int | 1, 2, 3… |
| `match_id` | string | `HOME-AWAY-seed` |
| `type` | string | see below |
| `period` | 1 or 2 | |
| `elapsed` | number | seconds of play since kickoff (half-time break excluded). Drives replay timing |
| `clock` | object | `{ minute, second, stoppage, display }`. `display` looks like `"23:41"`, or `"45:00 +2:13"` in stoppage time |
| `team` | `"home"`, `"away"` or null | team that performed the action |
| `player` | object or null | `{ id, name, number, position }`. `position` is the role in this match |
| `location` | `{x, y}` or null | where the action happened |
| `possession` | object | `{ id, team }`. A new id starts every time a team gains the ball |
| `score` | object | `{ home, away }` after this event |
| `data` | object | type-specific fields, below |

## Event types

| Type | `data` |
|---|---|
| `match_start` | `home`, `away` (`{id, name}`) |
| `period_start` | `period`, `announced_stoppage_minutes` |
| `kickoff` | `restart`: `period_1`, `period_2` or `goal` |
| `pass` | `recipient` (null if the pass failed), `intended_recipient`, `end_location`, `distance` (m), `progressive` (m toward goal, can be negative), `kind` (ground, long, cross, through), `set_piece` (corner or null), `difficulty` (0–1), `under_pressure`, `outcome` (complete, intercepted, out) |
| `carry` | `end_location`, `distance`, `top_speed_kmh`, `duration_sec`, `sprint`, `interrupted` |
| `pressure` | `target_player`, `speed_kmh` of the presser |
| `tackle` | `target_player`, `outcome` (won, lost, foul) |
| `interception` | `from_player` |
| `possession_change` | `from`, `to`, `reason` (interception, tackle, throw_in, goal_kick, save, block, foul, kickoff) |
| `foul` | `victim`, `penalty`, `card` (yellow, second_yellow, red or null) |
| `card` | `color` (yellow or red), `reason` |
| `corner` | none |
| `shot` | `xg`, `distance_to_goal`, `speed_kmh`, `body_part` (foot, head), `situation` (open_play, corner, free_kick, penalty), `under_pressure`, `key_pass_player`, `outcome` (goal, saved, blocked, off_target) |
| `goal` | `shot_id`, `scorer`, `assist`, `xg`, `situation`, `score_after` |
| `save` | `shot_id`, `shooter`, `speed_kmh`, `xg` |
| `block` | `shot_id`, `shooter` |
| `substitution` | `player_out`, `player_in`, `role` (`player` is the player coming on) |
| `period_end` | `period`, `score` |
| `match_end` | `final_score` |

## Modelled but not labelled

Momentum is a hidden value that drifts during the match. It shifts after goals, big chances and red cards, and it changes how teams press, pass and shoot. It is **not** in the events. Detecting those spells from the raw events is the Analyst's job.
