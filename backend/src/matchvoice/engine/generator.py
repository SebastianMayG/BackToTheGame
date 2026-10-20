"""Synthetic, football-realistic match generator.

The simulation runs possession chains (pressure, tackles, passes, carries, shots, set pieces, fouls,
cards and substitutions) on a 105 x 68 m pitch. Every match is fully repeatable from its seed.

Internally the generator reasons in the *attacking frame* of the team on the ball
(ax = 0 own goal line, ax = 105 opponent goal line) and converts to absolute coordinates on output:
home attacks toward x = 105 in period 1 and toward x = 0 in period 2.

A hidden `momentum` value drifts during the match and changes how teams play. It is never written
to the events; detecting those spells from the raw events is the Analyst's job.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from matchvoice.engine.clubs import BENCH_ROLES, STARTING_ROLES, get_club, role_group
from matchvoice.models import (
    Clock,
    Club,
    Location,
    Match,
    MatchEvent,
    MatchMeta,
    Player,
    PlayerRef,
    Possession,
    Score,
    Side,
)

PITCH_L = 105.0
PITCH_W = 68.0
HALF = 45 * 60
GOAL_Y = PITCH_W / 2
BOX_X = PITCH_L - 16.5
BOX_Y_MIN, BOX_Y_MAX = 13.84, 54.16

# Role group weights by zone of the pitch (attacking frame): who tends to have the ball there.
_ZONE_WEIGHTS = {
    "def": {"GK": 0.06, "CB": 0.36, "FB": 0.28, "MID": 0.28, "WING": 0.01, "ST": 0.01},
    "mid": {"GK": 0.0, "CB": 0.12, "FB": 0.2, "MID": 0.42, "WING": 0.16, "ST": 0.1},
    "att": {"GK": 0.0, "CB": 0.03, "FB": 0.1, "MID": 0.25, "WING": 0.32, "ST": 0.3},
    "box": {"GK": 0.0, "CB": 0.08, "FB": 0.04, "MID": 0.18, "WING": 0.25, "ST": 0.45},
}


def _clip(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _zone(ax: float) -> str:
    if ax < 35:
        return "def"
    if ax < 70:
        return "mid"
    if ax < BOX_X:
        return "att"
    return "box"


def in_box(ax: float, ay: float) -> bool:
    return ax >= BOX_X and BOX_Y_MIN <= ay <= BOX_Y_MAX


def expected_goals(ax: float, ay: float, body: str = "foot", under_pressure: bool = False) -> float:
    """Simple xG model from distance and the angle the goal mouth subtends (attacking frame)."""
    dx = max(0.5, PITCH_L - ax)
    dy = ay - GOAL_Y
    dist = math.hypot(dx, dy)
    a = math.atan2(3.66 - dy, dx) - math.atan2(-3.66 - dy, dx)  # goal is 7.32 m wide
    logit = -0.25 - 0.17 * dist + 1.2 * abs(a)
    xg = 1 / (1 + math.exp(-logit))
    if body == "head":
        xg *= 0.55
    if under_pressure:
        xg *= 0.8
    return _clip(xg, 0.01, 0.9)


@dataclass
class _Team:
    side: Side
    club: Club
    lineup: dict[str, Player]  # match role -> player on the pitch
    bench: list[Player]
    sub_minutes: list[int]
    yellow: set[str] = field(default_factory=set)


class MatchGenerator:
    def __init__(self, home: Club, away: Club, seed: int):
        if home.id == away.id:
            raise ValueError("Home and away must be different clubs")
        self.rng = random.Random(seed)
        self.seed = seed
        self.match_id = f"{home.id}-{away.id}-{seed}"
        self.teams: dict[Side, _Team] = {
            "home": self._team("home", home),
            "away": self._team("away", away),
        }
        self.role_of: dict[str, str] = {p.id: role for t in self.teams.values() for role, p in t.lineup.items()}
        self.events: list[MatchEvent] = []
        self.period: int = 1
        self.period_t = 0.0
        self.elapsed = 0.0
        self.score: dict[Side, int] = {"home": 0, "away": 0}
        self.poss_id = 0
        self.poss_team: Side | None = None
        self.carrier: Player | None = None
        self.last_pass: tuple[Player, float, int] | None = None  # (passer, elapsed, possession id)
        self.ball = (PITCH_L / 2, GOAL_Y)
        self.momentum = 0.0  # hidden: > 0 favours home
        self.momentum_trace: list[tuple[float, float]] = []
        self.stoppage = {1: self.rng.randint(1, 4), 2: self.rng.randint(2, 6)}

    # ------------------------------------------------------------------ setup
    def _team(self, side: Side, club: Club) -> _Team:
        squad = {p.position: p for p in club.squad}
        lineup = {role: squad[role] for role in STARTING_ROLES}
        bench = [squad[r] for r in BENCH_ROLES]
        minutes = sorted(self.rng.sample(range(56, 86), 3))
        return _Team(side, club, lineup, bench, minutes)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def other(side: Side) -> Side:
        return "away" if side == "home" else "home"

    def attacks_right(self, side: Side) -> bool:
        return (side == "home") == (self.period == 1)

    def to_abs(self, side: Side, ax: float, ay: float) -> tuple[float, float]:
        if self.attacks_right(side):
            return ax, ay
        return PITCH_L - ax, PITCH_W - ay

    def to_af(self, side: Side, x: float, y: float) -> tuple[float, float]:
        return self.to_abs(side, x, y)  # the transform is its own inverse

    def mom(self, side: Side) -> float:
        return self.momentum if side == "home" else -self.momentum

    def clock(self) -> Clock:
        base = 0 if self.period == 1 else HALF
        if self.period_t <= HALF:
            total = int(base + self.period_t)
            m, s = divmod(total, 60)
            return Clock(minute=m, second=s, display=f"{m:02d}:{s:02d}")
        st = int(self.period_t - HALF)
        sm, ss = divmod(st, 60)
        mark = (base + HALF) // 60
        return Clock(minute=mark, second=0, stoppage=st, display=f"{mark:02d}:00 +{sm}:{ss:02d}")

    def ref(self, p: Player) -> PlayerRef:
        return PlayerRef(id=p.id, name=p.name, number=p.number, position=self.role_of.get(p.id, p.position))

    def emit(
        self,
        type_: str,
        side: Side | None = None,
        player: Player | None = None,
        loc: tuple[float, float] | None = None,
        **data: Any,
    ) -> MatchEvent:
        seq = len(self.events) + 1
        # Keep `data` JSON-shaped in memory too, so consumers see the same thing live and from a file.
        data = {k: v.model_dump() if isinstance(v, PlayerRef) else v for k, v in data.items()}
        ev = MatchEvent(
            id=f"{self.match_id}-{seq}",
            seq=seq,
            match_id=self.match_id,
            type=type_,  # type: ignore[arg-type]
            period=self.period,  # type: ignore[arg-type]
            elapsed=round(self.elapsed, 1),
            clock=self.clock(),
            team=side,
            player=self.ref(player) if player else None,
            location=Location(x=round(loc[0], 1), y=round(loc[1], 1)) if loc else None,
            possession=Possession(id=self.poss_id, team=self.poss_team),
            score=Score(home=self.score["home"], away=self.score["away"]),
            data=data,
        )
        self.events.append(ev)
        return ev

    def advance(self, dt: float) -> None:
        self.period_t += dt
        self.elapsed += dt
        self.momentum += self.rng.gauss(0, 0.018 * math.sqrt(dt))
        self.momentum *= 1 - 0.0012 * dt
        self.momentum = _clip(self.momentum, -1, 1)
        if not self.momentum_trace or self.elapsed - self.momentum_trace[-1][0] >= 30:
            self.momentum_trace.append((round(self.elapsed, 1), round(self.momentum, 3)))

    def nudge_momentum(self, side: Side, amount: float) -> None:
        self.momentum = _clip(self.momentum + (amount if side == "home" else -amount), -1, 1)

    def pick(self, side: Side, zone: str, exclude: Player | None = None) -> Player:
        lineup = self.teams[side].lineup
        weights = _ZONE_WEIGHTS[zone]
        options = [(p, weights[role_group(role)]) for role, p in lineup.items() if p is not exclude]
        total = sum(w for _, w in options)
        if total <= 0:
            return self.rng.choice([p for p, _ in options])
        r = self.rng.random() * total
        for p, w in options:
            r -= w
            if r <= 0:
                return p
        return options[-1][0]

    def keeper(self, side: Side) -> Player:
        lineup = self.teams[side].lineup
        return lineup.get("GK") or next(iter(lineup.values()))

    def by_group(self, side: Side, *groups: str) -> Player:
        options = [p for role, p in self.teams[side].lineup.items() if role_group(role) in groups]
        return self.rng.choice(options or list(self.teams[side].lineup.values()))

    def set_possession(self, side: Side, reason: str, carrier: Player) -> None:
        self.carrier = carrier
        if side == self.poss_team:
            return
        prev = self.poss_team
        self.poss_id += 1
        self.poss_team = side
        self.emit("possession_change", side, None, self.ball, **{"from": prev, "to": side, "reason": reason})

    def place_ball_af(self, side: Side, ax: float, ay: float) -> None:
        self.ball = self.to_abs(side, _clip(ax, 0.5, PITCH_L - 0.5), _clip(ay, 0.5, PITCH_W - 0.5))

    # ------------------------------------------------------------- the match
    def run(self) -> Match:
        home, away = self.teams["home"].club, self.teams["away"].club
        self.emit("match_start", home={"id": home.id, "name": home.name}, away={"id": away.id, "name": away.name})
        for period in (1, 2):
            self.period = period
            self.period_t = 0.0
            self.emit("period_start", period=period, announced_stoppage_minutes=self.stoppage[period])
            self.kickoff("home" if period == 1 else "away", restart=f"period_{period}")
            end = HALF + self.stoppage[period] * 60
            while self.period_t < end:
                self.maybe_substitute()
                self.step()
            self.poss_team = None
            self.emit(
                "period_end",
                None,
                None,
                None,
                period=period,
                score={"home": self.score["home"], "away": self.score["away"]},
            )
            if period == 1:
                self.ball = (PITCH_L / 2, GOAL_Y)
        self.emit("match_end", final_score={"home": self.score["home"], "away": self.score["away"]})
        meta = MatchMeta(
            match_id=self.match_id,
            seed=self.seed,
            home=home,
            away=away,
            stoppage_minutes={"1": self.stoppage[1], "2": self.stoppage[2]},
        )
        return Match(meta=meta, events=self.events)

    def kickoff(self, side: Side, restart: str = "goal") -> None:
        self.ball = (PITCH_L / 2, GOAL_Y)
        taker = self.teams[side].lineup.get("ST") or self.pick(side, "mid")
        self.set_possession(side, "kickoff", taker)
        self.emit("kickoff", side, taker, self.ball, restart=restart)
        self.advance(1.0)
        receiver = self.by_group(side, "MID")
        self.pass_to(side, taker, receiver, PITCH_L / 2 - 8, GOAL_Y + self.rng.uniform(-6, 6), "ground", 0.05, False)

    def maybe_substitute(self) -> None:
        minute = self.clock().minute
        if self.period != 2:
            return
        for side, team in self.teams.items():
            if not team.sub_minutes or minute < team.sub_minutes[0] or not team.bench:
                continue
            team.sub_minutes.pop(0)
            outfield = [(r, p) for r, p in team.lineup.items() if r != "GK" and p is not self.carrier]
            if not outfield:
                continue
            role, out = self.rng.choice(outfield)
            group = role_group(role)
            candidates = [p for p in team.bench if role_group(p.position) == group and p.position != "SUB_GK"]
            candidates = candidates or [p for p in team.bench if p.position != "SUB_GK"]
            if not candidates:
                continue
            new = candidates[0]
            team.bench.remove(new)
            team.lineup[role] = new
            self.role_of[new.id] = role
            self.advance(self.rng.uniform(15, 35))
            self.emit("substitution", side, new, None, player_out=self.ref(out), player_in=self.ref(new), role=role)

    # ------------------------------------------------------------- one step
    def step(self) -> None:
        side = self.poss_team or "home"
        opp = self.other(side)
        carrier = self.carrier or self.pick(side, "mid")
        club, oclub = self.teams[side].club, self.teams[opp].club
        ax, ay = self.to_af(side, *self.ball)
        m = self.mom(side)

        under = False
        if ax >= BOX_X - 4:
            press_p = 0.55  # every team defends its own box hard, whatever its pressing style
        else:
            press_p = oclub.style.press * (0.38 if ax < 35 else 0.27 if ax < 70 else 0.3)
        press_p *= 1 - 0.4 * m
        if role_group(self.role_of[carrier.id]) == "GK":
            press_p *= 0.3
        if self.rng.random() < press_p:
            presser = self.pick(opp, _zone(PITCH_L - ax))
            self.emit(
                "pressure",
                opp,
                presser,
                self.ball,
                target_player=self.ref(carrier),
                speed_kmh=round(self.rng.uniform(16, presser.top_speed_kmh * 0.95), 1),
            )
            under = True
            self.advance(0.6)
            if self.rng.random() < 0.3:
                r = self.rng.random()
                win_p = 0.5 + (oclub.style.quality - club.style.quality) - 0.15 * m
                if r < win_p:
                    self.emit("tackle", opp, presser, self.ball, target_player=self.ref(carrier), outcome="won")
                    self.set_possession(opp, "tackle", presser)
                    self.advance(1.2)
                    return
                if r < win_p + 0.2 and not (in_box(ax, ay) and self.rng.random() < 0.82):
                    self.emit("tackle", opp, presser, self.ball, target_player=self.ref(carrier), outcome="foul")
                    self.foul(presser, carrier, side)
                    return
                self.emit("tackle", opp, presser, self.ball, target_player=self.ref(carrier), outcome="lost")

        # A deep defensive block wins many balls in and around its own box.
        if ax > 72:
            block_p = (0.32 if in_box(ax, ay) else 0.19) * (1 - 0.3 * m) * (1.6 - club.style.quality)
            if self.rng.random() < block_p:
                defender = self.by_group(opp, "CB", "FB", "MID")
                self.emit("tackle", opp, defender, self.ball, target_player=self.ref(carrier), outcome="won")
                self.set_possession(opp, "tackle", defender)
                self.advance(1.5)
                return

        dist_goal = math.hypot(PITCH_L - ax, GOAL_Y - ay)
        if dist_goal < 11:
            shoot_p = 0.5
        elif dist_goal < 18:
            shoot_p = 0.42
        elif dist_goal < 25:
            shoot_p = 0.16
        elif dist_goal < 32:
            shoot_p = 0.05
        else:
            shoot_p = 0.0
        shoot_p *= (0.8 + 0.4 * club.style.directness) * (1 + 0.4 * m)

        r = self.rng.random()
        if r < shoot_p:
            lp = self.last_pass
            key_passer = (
                lp[0] if lp and lp[2] == self.poss_id and self.elapsed - lp[1] < 15 and lp[0] is not carrier else None
            )
            body = "head" if key_passer and self.rng.random() < 0.25 and ax > BOX_X else "foot"
            self.shot(side, carrier, "open_play", body, under, key_passer)
        elif r < shoot_p + 0.2 and role_group(self.role_of[carrier.id]) != "GK":
            self.carry(side, carrier, ax, ay, under)
        else:
            self.pass_(side, carrier, ax, ay, under)

    # --------------------------------------------------------------- actions
    def pass_(self, side: Side, carrier: Player, ax: float, ay: float, under: bool) -> None:
        st = self.teams[side].club.style
        rng = self.rng
        r = rng.random()
        is_gk = role_group(self.role_of[carrier.id]) == "GK"
        if ax > 70 and (ay < 15 or ay > 53) and r < 0.35:
            kind, tx, ty = "cross", rng.uniform(92, 101), rng.uniform(24, 44)
        elif ax > 62 and r < 0.16:
            kind, tx, ty = "through", ax + rng.uniform(8, 20), ay + rng.gauss(0, 7)
        elif ax < 60 and (r < 0.05 + 0.12 * st.directness or (is_gk and r < 0.45)):
            kind, tx, ty = "long", ax + rng.uniform(22, 42), rng.uniform(6, 62)
        else:
            kind = "ground"
            tx = ax + rng.gauss(3 + 5 * st.directness, 9)
            ty = ay + rng.gauss(0, 9 + 6 * st.width)
        tx, ty = _clip(tx, 1, 104), _clip(ty, 0.5, 67.5)
        dist = math.hypot(tx - ax, ty - ay)
        progressive = tx - ax
        difficulty = (
            0.05
            + dist / 80
            + (0.14 if under else 0)
            + {"cross": 0.25, "through": 0.28, "long": 0.12}.get(kind, 0.0)
            + (0.08 if tx > BOX_X else 0)
            + max(0.0, progressive) / 150
        )
        difficulty = _clip(difficulty, 0.02, 0.98)
        receiver = self.pick(side, _zone(tx), exclude=carrier)
        self.pass_to(side, carrier, receiver, tx, ty, kind, difficulty, under, ax, ay)

    def pass_to(
        self,
        side: Side,
        carrier: Player,
        receiver: Player,
        tx: float,
        ty: float,
        kind: str,
        difficulty: float,
        under: bool,
        ax: float | None = None,
        ay: float | None = None,
        set_piece: str | None = None,
    ) -> bool:
        rng = self.rng
        if ax is None or ay is None:
            ax, ay = self.to_af(side, *self.ball)
        m = self.mom(side)
        dist = math.hypot(tx - ax, ty - ay)
        # Defences get denser near their own goal.
        density = 0.32 if in_box(tx, ty) else 0.08 if tx > 75 else 0.0
        p_success = _clip(0.99 - 0.44 * difficulty - density + (carrier.quality - 0.75) * 0.6 + 0.06 * m, 0.12, 0.98)
        end = self.to_abs(side, tx, ty)
        base = {
            "intended_recipient": self.ref(receiver),
            "end_location": {"x": round(end[0], 1), "y": round(end[1], 1)},
            "distance": round(dist, 1),
            "progressive": round(tx - ax, 1),
            "kind": kind,
            "set_piece": set_piece,
            "difficulty": round(difficulty, 2),
            "under_pressure": under,
        }
        if rng.random() < p_success:
            self.emit("pass", side, carrier, self.ball, recipient=self.ref(receiver), outcome="complete", **base)
            self.last_pass = (carrier, self.elapsed, self.poss_id)
            self.ball = end
            self.carrier = receiver
            self.advance(0.8 + dist / 14 + rng.uniform(0.3, 2.0))
            return True

        opp = self.other(side)
        if rng.random() < 0.8 or tx >= 104:
            self.emit("pass", side, carrier, self.ball, recipient=None, outcome="intercepted", **base)
            self.advance(0.8 + dist / 15)
            self.ball = end
            interceptor = self.pick(opp, _zone(PITCH_L - tx))
            self.emit("interception", opp, interceptor, self.ball, from_player=self.ref(carrier))
            if kind == "cross" and set_piece is None and rng.random() < 0.3:
                self.corner(side)  # cleared behind for a corner
                return False
            self.set_possession(opp, "interception", interceptor)
            return False

        self.emit("pass", side, carrier, self.ball, recipient=None, outcome="out", **base)
        self.advance(rng.uniform(6, 14))
        if tx > 100:
            self.goal_kick(opp)
        else:
            touch_y = 0.3 if ty < GOAL_Y else PITCH_W - 0.3
            self.place_ball_af(side, tx, touch_y)
            self.set_possession(opp, "throw_in", self.by_group(opp, "FB", "WING"))
        return False

    def carry(self, side: Side, carrier: Player, ax: float, ay: float, under: bool) -> None:
        rng = self.rng
        group = role_group(self.role_of[carrier.id])
        sprint_p = 0.32 if group in ("WING", "FB") else 0.16
        sprint = rng.random() < sprint_p and ax < 92
        dist = rng.uniform(12, 32) if sprint else rng.uniform(3, 11)
        max_x = 95 if sprint else 99
        theta = rng.gauss(0, 0.55)
        tx = _clip(ax + dist * math.cos(theta), 1, max(ax, max_x))
        ty = _clip(ay + dist * math.sin(theta), 1, 67)
        dist = math.hypot(tx - ax, ty - ay)
        speed = carrier.top_speed_kmh * rng.uniform(0.86, 1.0) if sprint else rng.uniform(9, 22)
        duration = dist / (speed / 3.6) * 1.12
        end = self.to_abs(side, tx, ty)

        # A defender may step in during the run: win the ball cleanly or bring the carrier down.
        opp = self.other(side)
        duel: str | None = None
        if under or rng.random() < 0.15 or in_box(tx, ty):
            r = rng.random()
            foul_p = 0.012 if in_box(tx, ty) else 0.1
            duel = "won" if r < 0.12 else "foul" if r < 0.12 + foul_p else None
        interrupted = duel is not None
        self.emit(
            "carry",
            side,
            carrier,
            self.ball,
            end_location={"x": round(end[0], 1), "y": round(end[1], 1)},
            distance=round(dist, 1),
            top_speed_kmh=round(speed, 1),
            duration_sec=round(duration, 1),
            sprint=sprint,
            interrupted=interrupted,
        )
        self.advance(duration)
        self.ball = end
        if duel:
            defender = self.pick(opp, _zone(PITCH_L - tx))
            if duel == "won":
                self.emit("tackle", opp, defender, self.ball, target_player=self.ref(carrier), outcome="won")
                self.set_possession(opp, "tackle", defender)
            else:
                self.emit("tackle", opp, defender, self.ball, target_player=self.ref(carrier), outcome="foul")
                self.foul(defender, carrier, side)

    def shot(
        self,
        side: Side,
        shooter: Player,
        situation: str,
        body: str,
        under: bool,
        key_passer: Player | None,
    ) -> None:
        rng = self.rng
        opp = self.other(side)
        ax, ay = self.to_af(side, *self.ball)
        dist = math.hypot(PITCH_L - ax, GOAL_Y - ay)
        if situation in ("open_play", "corner") and in_box(ax, ay) and rng.random() < 0.7:
            under = True  # the box is crowded: most shots there are contested
        if situation == "penalty":
            xg = 0.76
        elif situation == "free_kick":
            xg = _clip(0.11 - 0.002 * dist, 0.03, 0.09)
        else:
            xg = expected_goals(ax, ay, body, under)
            if situation == "corner" or (key_passer is not None and body == "head"):
                xg *= 0.55  # a header from a cross is rarely clean
        speed = rng.uniform(38, 68) if body == "head" else _clip(rng.gauss(72 + dist * 1.0, 10), 50, 128)
        keeper = self.keeper(opp)
        m = self.mom(side)
        p_goal = xg * (1 - (keeper.quality - 0.75) * 0.6) * (1 + 0.12 * m) * (0.85 + 0.3 * shooter.quality)
        p_goal = min(p_goal, 0.8)
        r = rng.random()
        if situation != "penalty" and under and rng.random() < 0.3:
            outcome = "blocked"
        elif r < p_goal:
            outcome = "goal"
        elif r < p_goal + 0.27 + 0.25 * xg:
            outcome = "saved"
        else:
            outcome = "off_target"

        shot_ev = self.emit(
            "shot",
            side,
            shooter,
            self.ball,
            xg=round(xg, 3),
            distance_to_goal=round(dist, 1),
            speed_kmh=round(speed, 1),
            body_part=body,
            situation=situation,
            under_pressure=under,
            key_pass_player=self.ref(key_passer) if key_passer else None,
            outcome=outcome,
        )
        self.advance(1.0)

        if outcome == "goal":
            self.score[side] += 1
            self.emit(
                "goal",
                side,
                shooter,
                self.ball,
                shot_id=shot_ev.id,
                scorer=self.ref(shooter),
                assist=self.ref(key_passer) if key_passer else None,
                xg=round(xg, 3),
                situation=situation,
                score_after={"home": self.score["home"], "away": self.score["away"]},
            )
            self.nudge_momentum(opp, 0.12)  # the team behind pushes
            self.advance(rng.uniform(50, 80))
            self.kickoff(opp)
            return

        if xg >= 0.25:
            self.nudge_momentum(side, 0.1)
        if outcome == "saved":
            self.emit(
                "save",
                opp,
                keeper,
                self.to_abs(side, 104.5, GOAL_Y),
                shot_id=shot_ev.id,
                shooter=self.ref(shooter),
                speed_kmh=round(speed, 1),
                xg=round(xg, 3),
            )
            if rng.random() < 0.33:
                self.corner(side)
            else:
                self.place_ball_af(side, 99, GOAL_Y)
                self.set_possession(opp, "save", keeper)
                self.advance(rng.uniform(3, 8))
        elif outcome == "blocked":
            blocker = self.by_group(opp, "CB", "FB", "MID")
            self.emit("block", opp, blocker, self.ball, shot_id=shot_ev.id, shooter=self.ref(shooter))
            r2 = rng.random()
            if r2 < 0.38:
                self.corner(side)
            elif r2 < 0.72:
                self.set_possession(opp, "block", blocker)
            else:
                self.place_ball_af(side, ax - 9, ay + rng.uniform(-8, 8))
                self.carrier = self.by_group(side, "MID", "FB")
        else:
            self.advance(rng.uniform(15, 28))
            self.goal_kick(opp)

    def goal_kick(self, side: Side) -> None:
        self.place_ball_af(side, 5.5, GOAL_Y)
        self.set_possession(side, "goal_kick", self.keeper(side))

    def corner(self, side: Side) -> None:
        rng = self.rng
        cy = 0.5 if rng.random() < 0.5 else PITCH_W - 0.5
        self.advance(rng.uniform(18, 30))
        self.place_ball_af(side, PITCH_L - 0.5, cy)
        taker = self.by_group(side, "WING", "MID")
        self.carrier = taker
        self.emit("corner", side, taker, self.ball)
        self.advance(2.0)
        target = self.pick(side, "box", exclude=taker)
        tx, ty = rng.uniform(94, 101), rng.uniform(26, 42)
        if self.pass_to(side, taker, target, tx, ty, "cross", 0.62, False, set_piece="corner"):
            if rng.random() < 0.72:
                body = "head" if rng.random() < 0.7 else "foot"
                self.shot(side, target, "corner", body, rng.random() < 0.5, taker)

    def foul(self, fouler: Player, victim: Player, fouled_side: Side) -> None:
        rng = self.rng
        opp = self.other(fouled_side)
        team = self.teams[opp]
        ax, ay = self.to_af(fouled_side, *self.ball)
        penalty = in_box(ax, ay)
        card = None
        r = rng.random()
        if r < 0.006:
            card = "red"
        elif r < 0.14 + (0.1 if penalty else 0):
            card = "second_yellow" if fouler.id in team.yellow else "yellow"
        self.emit("foul", opp, fouler, self.ball, victim=self.ref(victim), penalty=penalty, card=card)
        if card:
            color = "yellow" if card == "yellow" else "red"
            team.yellow.add(fouler.id)
            self.emit(
                "card",
                opp,
                fouler,
                self.ball,
                color=color,
                reason="second_yellow" if card == "second_yellow" else "foul",
            )
            if color == "red":
                role = self.role_of.get(fouler.id)
                if role and team.lineup.get(role) is fouler:
                    del team.lineup[role]
                self.nudge_momentum(fouled_side, 0.15)
        self.advance(rng.uniform(15, 40) if not penalty else rng.uniform(50, 80))
        self.set_possession(fouled_side, "foul", victim)

        if penalty:
            taker = self.teams[fouled_side].lineup.get("ST") or victim
            self.place_ball_af(fouled_side, PITCH_L - 11, GOAL_Y)
            self.carrier = taker
            self.shot(fouled_side, taker, "penalty", "foot", False, None)
        elif ax >= 75 and abs(ay - GOAL_Y) < 18 and rng.random() < 0.45:
            taker = self.by_group(fouled_side, "MID", "WING", "ST")
            self.carrier = taker
            self.shot(fouled_side, taker, "free_kick", "foot", False, None)


def generate_match(seed: int = 42, home: str = "NVR", away: str = "KBY") -> Match:
    return MatchGenerator(get_club(home), get_club(away), seed).run()
