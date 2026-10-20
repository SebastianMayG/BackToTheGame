"""The Analyst: reads events one at a time, keeps live team and player stats and flags key moments.

Plain code, no AI: instant and always right. Each moment carries its evidence (`facts`, `event_ids`)
and a template headline per language. AI agents explain and narrate on top of it.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from matchvoice.engine.narration import moment_headline
from matchvoice.models import (
    Lang,
    MatchEvent,
    MatchMeta,
    Moment,
    PlayerRef,
    PlayerStats,
    Score,
    Side,
    StatsSnapshot,
    TeamStats,
)

LANGS: tuple[Lang, ...] = ("es", "en")
BOX_X = 105 - 16.5
WINDOW = 5 * 60  # seconds used for momentum, rhythm and pressing reads


def _other(side: Side) -> Side:
    return "away" if side == "home" else "home"


def _in_box(ax: float, ay: float) -> bool:
    return ax >= BOX_X and 13.84 <= ay <= 54.16


@dataclass
class _TeamAcc:
    stats: TeamStats = field(default_factory=TeamStats)
    possession_sec: float = 0.0
    opp_build_up_passes: int = 0  # opponent passes in their own 60% (PPDA numerator)
    high_def_actions: int = 0  # our defensive actions in that same zone (PPDA denominator)


class Analyst:
    def __init__(self, meta: MatchMeta):
        self.meta = meta
        self.teams: dict[Side, _TeamAcc] = {"home": _TeamAcc(), "away": _TeamAcc()}
        self.players: dict[str, PlayerStats] = {}
        self.moments: list[Moment] = []
        self.score = Score()
        self.elapsed = 0.0
        self.period = 1
        self.clock = "00:00"
        self._last_poss: tuple[Side | None, float] = (None, 0.0)
        self._threat: deque[tuple[float, Side, float]] = deque()  # (elapsed, side, value)
        self._poss_changes: deque[float] = deque()
        self._poss_changes_total = 0
        self._regains: deque[tuple[float, Side]] = deque()  # high regains
        self._recent_poss: deque[tuple[float, Side, float]] = deque()
        self._cooldown: dict[str, float] = {}
        self._last_swing_side: Side | None = None
        self._last_check = 0.0
        self._last_event: MatchEvent | None = None

    # ------------------------------------------------------------ helpers
    def _af(self, ev: MatchEvent, x: float, y: float, side: Side | None = None) -> tuple[float, float]:
        side = side or ev.team
        if side is None:
            return x, y
        attacks_right = (side == "home") == (ev.period == 1)
        return (x, y) if attacks_right else (105 - x, 68 - y)

    def _player(self, ref: PlayerRef | dict[str, Any] | None, side: Side | None) -> PlayerStats | None:
        if ref is None or side is None:
            return None
        if isinstance(ref, dict):
            ref = PlayerRef(**ref)
        ps = self.players.get(ref.id)
        if ps is None:
            ps = PlayerStats(player=ref, team=side)
            self.players[ref.id] = ps
        else:
            ps.player = ref  # role may have changed after a substitution
        return ps

    def _team_name(self, side: Side | None) -> str:
        if side is None:
            return ""
        return (self.meta.home if side == "home" else self.meta.away).short_name

    def _ready(self, key: str, cooldown: float) -> bool:
        last = self._cooldown.get(key)
        if last is not None and self.elapsed - last < cooldown:
            return False
        self._cooldown[key] = self.elapsed
        return True

    def _moment(
        self,
        type_: str,
        importance: float,
        ev: MatchEvent,
        team: Side | None,
        players: list[PlayerRef | dict[str, Any] | None],
        facts: dict[str, Any],
        event_ids: list[str] | None = None,
    ) -> Moment:
        refs = [p if isinstance(p, PlayerRef) else PlayerRef(**p) for p in players if p]
        facts = {"team": self._team_name(team), "minute": ev.clock.display, **facts}
        m = Moment(
            id=f"m{len(self.moments) + 1}-{ev.seq}",
            type=type_,  # type: ignore[arg-type]
            importance=round(importance, 2),
            elapsed=ev.elapsed,
            clock=ev.clock.display,
            team=team,
            players=refs,
            facts=facts,
            event_ids=event_ids or [ev.id],
            headline={lang: moment_headline(type_, facts, lang) for lang in LANGS},
        )
        self.moments.append(m)
        return m

    def _add_threat(self, ev: MatchEvent, side: Side, value: float) -> None:
        self._threat.append((ev.elapsed, side, value))

    def _trim(self) -> None:
        cutoff = self.elapsed - WINDOW
        for dq in (self._threat, self._recent_poss):
            while dq and dq[0][0] < cutoff:
                dq.popleft()
        while self._poss_changes and self._poss_changes[0] < cutoff:
            self._poss_changes.popleft()
        while self._regains and self._regains[0][0] < cutoff:
            self._regains.popleft()

    def momentum(self) -> float:
        h = sum(v for _, s, v in self._threat if s == "home")
        a = sum(v for _, s, v in self._threat if s == "away")
        if h + a < 0.05:
            return 0.0
        return round((h - a) / (h + a), 3)

    def rhythm(self) -> str:
        if self.elapsed < 10 * 60 or self._poss_changes_total == 0:
            return "balanced"
        window = min(WINDOW, self.elapsed)
        recent_rate = len(self._poss_changes) / window
        avg_rate = self._poss_changes_total / self.elapsed
        if recent_rate > avg_rate * 1.35:
            return "chaos"
        if recent_rate < avg_rate * 0.7:
            return "control"
        return "balanced"

    # ------------------------------------------------------------ main entry
    def process(self, ev: MatchEvent) -> list[Moment]:
        """Update stats with one event and return the key moments it triggered."""
        before = len(self.moments)
        # possession time (dead time included, which is fine for a share)
        last_side, last_t = self._last_poss
        if last_side is not None and ev.elapsed > last_t:
            self.teams[last_side].possession_sec += ev.elapsed - last_t
            self._recent_poss.append((ev.elapsed, last_side, ev.elapsed - last_t))
        self._last_poss = (ev.possession.team, ev.elapsed)
        self.elapsed = ev.elapsed
        self.period = ev.period
        self.clock = ev.clock.display
        self.score = ev.score

        handler = getattr(self, f"_on_{ev.type}", None)
        if handler:
            handler(ev)

        self._trim()
        if ev.elapsed - self._last_check >= 20:
            self._last_check = ev.elapsed
            self._periodic(ev)
        self._last_event = ev
        return self.moments[before:]

    # ------------------------------------------------------------ handlers
    def _on_pass(self, ev: MatchEvent) -> None:
        side = ev.team
        assert side and ev.location
        d = ev.data
        t = self.teams[side].stats
        ps = self._player(ev.player, side)
        t.passes += 1
        if ps:
            ps.passes += 1
        ax, ay = self._af(ev, ev.location.x, ev.location.y)
        if ax <= 63:
            self.teams[_other(side)].opp_build_up_passes += 1
        if d["outcome"] != "complete":
            return
        t.passes_completed += 1
        if ps:
            ps.passes_completed += 1
        end = d["end_location"]
        ex, ey = self._af(ev, end["x"], end["y"])
        if ax >= 70:
            t.final_third_passes += 1
            self._add_threat(ev, side, 0.01)
        if d["progressive"] >= 10 and ex >= 52.5:
            t.progressive_passes += 1
            if ps:
                ps.progressive_passes += 1
        if _in_box(ex, ey) and not _in_box(ax, ay):
            t.box_entries += 1
            self._add_threat(ev, side, 0.04)
        if d["difficulty"] >= 0.6 and d["progressive"] >= 15 and self._ready("quality_pass", 180):
            self._moment(
                "quality_pass",
                0.4,
                ev,
                side,
                [ev.player, d.get("recipient")],
                {
                    "player": ev.player.name if ev.player else "",
                    "distance": round(d["distance"]),
                    "difficulty": d["difficulty"],
                    "progressive": d["progressive"],
                },
            )

    def _on_carry(self, ev: MatchEvent) -> None:
        side = ev.team
        assert side and ev.location
        d = ev.data
        ps = self._player(ev.player, side)
        if ps:
            ps.carry_distance_m = round(ps.carry_distance_m + d["distance"], 1)
            ps.top_speed_kmh = max(ps.top_speed_kmh, d["top_speed_kmh"])
            if d["sprint"]:
                ps.sprints += 1
        ax, ay = self._af(ev, ev.location.x, ev.location.y)
        ex, ey = self._af(ev, d["end_location"]["x"], d["end_location"]["y"])
        if _in_box(ex, ey) and not _in_box(ax, ay):
            self.teams[side].stats.box_entries += 1
            self._add_threat(ev, side, 0.04)
        if d["sprint"] and d["top_speed_kmh"] >= 33 and ev.player and self._ready(f"speed:{ev.player.id}", 600):
            self._moment(
                "speed_alert",
                0.3,
                ev,
                side,
                [ev.player],
                {"player": ev.player.name, "speed": d["top_speed_kmh"], "distance": round(d["distance"])},
            )

    def _on_pressure(self, ev: MatchEvent) -> None:
        if ev.team:
            self.teams[ev.team].stats.pressures += 1
            ps = self._player(ev.player, ev.team)
            if ps:
                ps.pressures += 1

    def _defensive_action(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None or ev.location is None:
            return
        ax, _ = self._af(ev, ev.location.x, ev.location.y)
        if ax >= 42:  # inside the opponent's own 60%
            self.teams[side].high_def_actions += 1
        if ax >= 52.5:
            self._regains.append((ev.elapsed, side))

    def _on_tackle(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None:
            return
        self._defensive_action(ev)
        if ev.data["outcome"] == "won":
            self.teams[side].stats.tackles_won += 1
            ps = self._player(ev.player, side)
            if ps:
                ps.tackles_won += 1

    def _on_interception(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None:
            return
        self._defensive_action(ev)
        self.teams[side].stats.interceptions += 1
        ps = self._player(ev.player, side)
        if ps:
            ps.interceptions += 1

    def _on_possession_change(self, ev: MatchEvent) -> None:
        if ev.data.get("reason") in ("interception", "tackle", "block", "save"):
            self._poss_changes.append(ev.elapsed)
            self._poss_changes_total += 1

    def _on_foul(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None:
            return
        self.teams[side].stats.fouls += 1
        if ev.data.get("penalty"):
            victim_side = _other(side)
            self._moment(
                "penalty_awarded",
                0.85,
                ev,
                victim_side,
                [ev.data.get("victim"), ev.player],
                {"victim": ev.data["victim"]["name"], "fouler": ev.player.name if ev.player else ""},
            )

    def _on_card(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None or ev.player is None:
            return
        ps = self._player(ev.player, side)
        if ev.data["color"] == "red":
            self.teams[side].stats.red_cards += 1
            if ps:
                ps.red_cards += 1
            self._moment(
                "red_card", 0.9, ev, side, [ev.player], {"player": ev.player.name, "reason": ev.data.get("reason")}
            )
        else:
            self.teams[side].stats.yellow_cards += 1
            if ps:
                ps.yellow_cards += 1
            self._moment("yellow_card", 0.35, ev, side, [ev.player], {"player": ev.player.name})

    def _on_corner(self, ev: MatchEvent) -> None:
        if ev.team:
            self.teams[ev.team].stats.corners += 1
            self._add_threat(ev, ev.team, 0.03)

    def _on_shot(self, ev: MatchEvent) -> None:
        side = ev.team
        assert side
        d = ev.data
        t = self.teams[side].stats
        ps = self._player(ev.player, side)
        t.shots += 1
        t.xg = round(t.xg + d["xg"], 3)
        t.top_shot_speed_kmh = max(t.top_shot_speed_kmh, d["speed_kmh"])
        on_target = d["outcome"] in ("goal", "saved")
        if on_target:
            t.shots_on_target += 1
        if ps:
            ps.shots += 1
            ps.xg = round(ps.xg + d["xg"], 3)
            if on_target:
                ps.shots_on_target += 1
        kp = self._player(d.get("key_pass_player"), side)
        if kp:
            kp.key_passes += 1
        self._add_threat(ev, side, d["xg"])
        name = ev.player.name if ev.player else ""
        if d["outcome"] in ("off_target", "blocked") and d["xg"] >= 0.3:
            self._moment(
                "big_chance",
                0.7,
                ev,
                side,
                [ev.player],
                {"shooter": name, "xg": d["xg"], "xg_pct": round(d["xg"] * 100), "outcome": d["outcome"]},
            )
        if d["speed_kmh"] >= 110 and self._ready("rocket_shot", 240):
            self._moment(
                "rocket_shot",
                0.45,
                ev,
                side,
                [ev.player],
                {"player": name, "speed": d["speed_kmh"], "outcome": d["outcome"]},
            )

    def _on_save(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None:
            return
        self.teams[side].stats.saves += 1
        ps = self._player(ev.player, side)
        if ps:
            ps.saves += 1
        d = ev.data
        xg = d.get("xg", 0.0)
        if xg >= 0.15 or (d["speed_kmh"] >= 105 and xg >= 0.05):
            self._moment(
                "great_save",
                0.55 + min(0.3, xg),
                ev,
                side,
                [ev.player, d.get("shooter")],
                {
                    "keeper": ev.player.name if ev.player else "",
                    "shooter": d["shooter"]["name"],
                    "speed": d["speed_kmh"],
                    "xg": xg,
                    "xg_pct": round(xg * 100),
                },
                [d["shot_id"], ev.id],
            )

    def _on_block(self, ev: MatchEvent) -> None:
        self._defensive_action(ev)

    def _on_goal(self, ev: MatchEvent) -> None:
        side = ev.team
        assert side
        d = ev.data
        self.teams[side].stats.goals += 1
        scorer = self._player(d["scorer"], side)
        if scorer:
            scorer.goals += 1
        assist = self._player(d.get("assist"), side)
        if assist:
            assist.assists += 1
        after = d["score_after"]
        mine, theirs = after[side], after[_other(side)]
        context: list[str] = []
        if mine + theirs == 1:
            context.append("opener")
        elif mine == theirs:
            context.append("equaliser")
        elif mine == theirs + 1:
            context.append("go_ahead")
        elif mine > theirs + 1:
            context.append("extends_lead")
        else:
            context.append("consolation")
        mom = self.momentum()
        if (side == "home" and mom < -0.4) or (side == "away" and mom > 0.4):
            context.append("against_run")
        if scorer and scorer.goals == 2:
            context.append("brace")
        elif scorer and scorer.goals == 3:
            context.append("hat_trick")
        self._moment(
            "goal",
            1.0,
            ev,
            side,
            [d["scorer"], d.get("assist")],
            {
                "scorer": d["scorer"]["name"],
                "assist": d["assist"]["name"] if d.get("assist") else None,
                "xg": d["xg"],
                "situation": d["situation"],
                "score_after": after,
                "context": context,
                "momentum_before": mom,
            },
            [d["shot_id"], ev.id],
        )

    def _on_substitution(self, ev: MatchEvent) -> None:
        side = ev.team
        if side is None:
            return
        self._player(ev.data["player_in"], side)
        self._moment(
            "substitution",
            0.3,
            ev,
            side,
            [ev.data["player_in"], ev.data["player_out"]],
            {"player_in": ev.data["player_in"]["name"], "player_out": ev.data["player_out"]["name"]},
        )

    def _on_period_end(self, ev: MatchEvent) -> None:
        snap = self.snapshot()
        kind = "half_time" if ev.data["period"] == 1 else "full_time"
        self._moment(
            kind,
            0.8 if kind == "half_time" else 1.0,
            ev,
            None,
            [p.player for p in snap.top_players[:1]],
            {
                "home": self.meta.home.short_name,
                "away": self.meta.away.short_name,
                "h": ev.score.home,
                "a": ev.score.away,
                "xg_home": round(snap.home.xg, 2),
                "xg_away": round(snap.away.xg, 2),
                "possession_home": snap.home.possession_pct,
                "shots_home": snap.home.shots,
                "shots_away": snap.away.shots,
                "top_player": snap.top_players[0].player.name if snap.top_players else None,
            },
        )

    # ---------------------------------------------------------- periodic reads
    def _periodic(self, ev: MatchEvent) -> None:
        if ev.type in ("period_end", "match_end"):
            return
        played = self.elapsed

        # Momentum swing: one team clearly owns the threat of the last five minutes.
        mom = self.momentum()
        threat_total = sum(v for _, _, v in self._threat)
        if played > 8 * 60 and abs(mom) >= 0.55 and threat_total >= 0.3:
            side: Side = "home" if mom > 0 else "away"
            if side != self._last_swing_side and self._ready("momentum_swing", 360):
                self._last_swing_side = side
                share = round((1 + abs(mom)) / 2 * 100)
                self._moment("momentum_swing", 0.6, ev, side, [], {"share": share, "momentum": mom})

        # Rhythm shift: control vs chaos.
        rhythm = self.rhythm()
        if rhythm != "balanced" and self._ready("rhythm_shift", 600):
            home_sec = sum(dt for _, s, dt in self._recent_poss if s == "home")
            total = sum(dt for _, _, dt in self._recent_poss) or 1
            home_share = home_sec / total
            dominant: Side = "home" if home_share >= 0.5 else "away"
            possession = round((home_share if dominant == "home" else 1 - home_share) * 100)
            if rhythm == "chaos" or possession >= 60:
                self._moment(
                    "rhythm_shift",
                    0.45,
                    ev,
                    dominant if rhythm == "control" else None,
                    [],
                    {"rhythm": rhythm, "changes": len(self._poss_changes), "possession": possession},
                )
            else:
                self._cooldown.pop("rhythm_shift", None)

        # Pressing spell: lots of high regains for one side.
        for side_ in ("home", "away"):
            regains = sum(1 for _, s in self._regains if s == side_)
            others = sum(1 for _, s in self._regains if s != side_)
            if regains >= 9 and regains >= 2.5 * max(1, others) and self._ready(f"press:{side_}", 600):
                self._moment("pressing_spell", 0.5, ev, side_, [], {"regains": regains})  # type: ignore[arg-type]

        # xG vs score: creating far more but not winning.
        if played > 30 * 60:
            for side_ in ("home", "away"):
                s_: Side = side_  # type: ignore[assignment]
                xg_for = self.teams[s_].stats.xg
                xg_against = self.teams[_other(s_)].stats.xg
                goals_for = getattr(self.score, s_)
                goals_against = getattr(self.score, _other(s_))
                if xg_for - xg_against >= 1.0 and goals_for <= goals_against and self._ready(f"xg:{s_}", 900):
                    self._moment(
                        "xg_vs_score",
                        0.55,
                        ev,
                        s_,
                        [],
                        {
                            "xg_for": round(xg_for, 2),
                            "xg_against": round(xg_against, 2),
                            "goals_for": goals_for,
                            "goals_against": goals_against,
                        },
                    )

    # ---------------------------------------------------------------- outputs
    def _rating(self, ps: PlayerStats) -> float:
        r = 6.0
        r += ps.goals * 0.9 + ps.assists * 0.6 + ps.xg * 0.5 + ps.key_passes * 0.15
        r += ps.progressive_passes * 0.025 + ps.tackles_won * 0.08 + ps.interceptions * 0.06 + ps.saves * 0.3
        if ps.passes >= 10:
            r += (ps.passes_completed / ps.passes - 0.8) * 1.5
        r -= ps.yellow_cards * 0.3 + ps.red_cards * 1.5
        r = 6.2 + (r - 6.0) * 0.6  # compress so only standout games reach 8+
        return round(max(3.0, min(10.0, r)), 1)

    def snapshot(self) -> StatsSnapshot:
        total_poss = sum(t.possession_sec for t in self.teams.values()) or 1.0
        ft_total = sum(t.stats.final_third_passes for t in self.teams.values()) or 1
        out: dict[Side, TeamStats] = {}
        for side, acc in self.teams.items():
            s = acc.stats.model_copy()
            s.goals = getattr(self.score, side)
            s.possession_pct = round(acc.possession_sec / total_poss * 100, 1)
            s.pass_accuracy = round(s.passes_completed / s.passes * 100, 1) if s.passes else 0.0
            s.field_tilt_pct = round(s.final_third_passes / ft_total * 100, 1)
            s.ppda = round(acc.opp_build_up_passes / acc.high_def_actions, 1) if acc.high_def_actions else None
            s.xg = round(s.xg, 2)
            out[side] = s
        for ps in self.players.values():
            ps.rating = self._rating(ps)
        top = sorted(self.players.values(), key=lambda p: p.rating, reverse=True)[:5]
        return StatsSnapshot(
            elapsed=self.elapsed,
            clock=self.clock,
            score=self.score,
            home=out["home"],
            away=out["away"],
            momentum=self.momentum(),
            rhythm=self.rhythm(),  # type: ignore[arg-type]
            top_players=[p.model_copy() for p in top],
        )

    def player_stats(self) -> list[PlayerStats]:
        for ps in self.players.values():
            ps.rating = self._rating(ps)
        return sorted(self.players.values(), key=lambda p: (p.team, p.player.number))
