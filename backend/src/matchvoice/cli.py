"""Command line tools: generate a match, print stats, check realism, list key moments, preview narration."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from matchvoice.engine.analyst import Analyst
from matchvoice.engine.generator import generate_match
from matchvoice.engine.narration import NarrationContext, narrate_event

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# Approximate per-team, per-match averages in a real top flight, for the realism check.
REAL = {
    "goals": "1.4",
    "shots": "12-13",
    "on_target": "4-5",
    "passes": "450-550",
    "pass_acc": "80-85%",
    "corners": "5",
    "fouls": "10-11",
    "yellows": "1.8",
}


def cmd_generate(args: argparse.Namespace) -> None:
    m = generate_match(args.seed, args.home, args.away)
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / f"match-{m.meta.match_id}.json"
    out.write_text(m.model_dump_json(indent=1), encoding="utf-8")
    print(f"{len(m.events)} events -> {out}")
    cmd_stats(args)


def cmd_stats(args: argparse.Namespace) -> None:
    m = generate_match(args.seed, args.home, args.away)
    a = Analyst(m.meta)
    for ev in m.events:
        a.process(ev)
    s = a.snapshot()
    print(f"\n{m.meta.home.name} {s.score.home} - {s.score.away} {m.meta.away.name}\n")
    rows = [
        ("xG", "xg"),
        ("Shots", "shots"),
        ("On target", "shots_on_target"),
        ("Possession %", "possession_pct"),
        ("Passes", "passes"),
        ("Pass accuracy %", "pass_accuracy"),
        ("Box entries", "box_entries"),
        ("Corners", "corners"),
        ("Fouls", "fouls"),
        ("Yellow cards", "yellow_cards"),
        ("PPDA", "ppda"),
        ("Field tilt %", "field_tilt_pct"),
    ]
    for label, key in rows:
        print(f"  {label:16s} {getattr(s.home, key)!s:>7}  {getattr(s.away, key)!s:>7}")
    print("\nTop players:")
    for p in s.top_players:
        print(f"  {p.rating:4.1f}  {p.player.name} ({p.team}, #{p.player.number})")


def cmd_calibrate(args: argparse.Namespace) -> None:
    agg: dict[str, list[float]] = {k: [] for k in REAL}
    for seed in range(args.n):
        m = generate_match(seed, args.home, args.away)
        for side in ("home", "away"):
            ev = [e for e in m.events if e.team == side]
            shots = [e for e in ev if e.type == "shot"]
            passes = [e for e in ev if e.type == "pass"]
            agg["goals"].append(sum(e.type == "goal" for e in ev))
            agg["shots"].append(len(shots))
            agg["on_target"].append(sum(e.data["outcome"] in ("goal", "saved") for e in shots))
            agg["passes"].append(len(passes))
            agg["pass_acc"].append(100 * sum(e.data["outcome"] == "complete" for e in passes) / max(1, len(passes)))
            agg["corners"].append(sum(e.type == "corner" for e in ev))
            agg["fouls"].append(sum(e.type == "foul" for e in ev))
            agg["yellows"].append(sum(e.type == "card" and e.data["color"] == "yellow" for e in ev))
    print(f"Realism check over {args.n} matches (per team per match)\n")
    print(f"  {'metric':10s} {'generator':>10s}  {'real (approx.)':>15s}")
    for k, values in agg.items():
        print(f"  {k:10s} {statistics.mean(values):10.2f}  {REAL[k]:>15s}")


def cmd_analyse(args: argparse.Namespace) -> None:
    m = generate_match(args.seed, args.home, args.away)
    a = Analyst(m.meta)
    for ev in m.events:
        for mo in a.process(ev):
            if mo.importance >= args.min:
                print(f"{mo.clock:>12s}  {mo.importance:.2f}  {mo.type:15s} {mo.headline[args.lang]}")


def cmd_narrate(args: argparse.Namespace) -> None:
    m = generate_match(args.seed, args.home, args.away)
    ctx = NarrationContext(meta=m.meta, lang=args.lang, mode=args.mode)
    for ev in m.events:
        line = narrate_event(ev, ctx)
        if line and line.level <= args.level:
            print(f"{line.clock:>12s}  [{line.level}] {line.text}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    parser = argparse.ArgumentParser(prog="matchvoice")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--seed", type=int, default=42)
        p.add_argument("--home", default="NVR")
        p.add_argument("--away", default="KBY")

    common(p := sub.add_parser("generate", help="Write a match JSON to data/ and print its box score"))
    p.set_defaults(fn=cmd_generate)
    common(p := sub.add_parser("stats", help="Print the box score"))
    p.set_defaults(fn=cmd_stats)
    common(p := sub.add_parser("calibrate", help="Compare averages with real football"))
    p.add_argument("--n", type=int, default=100)
    p.set_defaults(fn=cmd_calibrate)
    common(p := sub.add_parser("analyse", help="List the key moments the Analyst finds"))
    p.add_argument("--min", type=float, default=0.4)
    p.add_argument("--lang", default="es", choices=["es", "en"])
    p.set_defaults(fn=cmd_analyse)
    common(p := sub.add_parser("narrate", help="Print the template play-by-play"))
    p.add_argument("--lang", default="es", choices=["es", "en"])
    p.add_argument("--mode", default="fan", choices=["fan", "analyst", "accessible"])
    p.add_argument("--level", type=int, default=2)
    p.set_defaults(fn=cmd_narrate)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
