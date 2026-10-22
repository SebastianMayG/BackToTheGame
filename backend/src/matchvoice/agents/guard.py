"""Grounding guard: every number and proper name in AI text must come from the Analyst's evidence."""

from __future__ import annotations

import re
from typing import Any

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)
SENTENCE_START = re.compile(r"(?:^|[.!?¡¿:]\s*)$")

# Football terms that are written in capitals but are not names.
ALLOWED_WORDS = {"xg", "ppda", "var", "i", "a", "el", "la", "los", "las"}


def _numbers_in(value: Any) -> list[float]:
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        return [float(n.replace(",", ".")) for n in NUMBER.findall(value)]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers_in(v)]
    if isinstance(value, (list, tuple)):
        return [n for v in value for n in _numbers_in(v)]
    return []


def _words_in(value: Any) -> set[str]:
    if isinstance(value, str):
        return {w.lower() for w in WORD.findall(value)}
    if isinstance(value, dict):
        return {w for v in value.values() for w in _words_in(v)}
    if isinstance(value, (list, tuple)):
        return {w for v in value for w in _words_in(v)}
    return set()


def allowed_numbers(moment: dict) -> set[float]:
    """Facts, the clock, and the usual roundings of each fact (xG 0.179 -> 0.18 -> 18%)."""
    allowed: set[float] = set()
    for v in _numbers_in(moment.get("facts", {})) + _numbers_in(moment.get("clock", "")):
        allowed.update({v, round(v), round(v, 1), round(v, 2), round(v, 3), round(v * 100), round(v * 100, 1)})
    return allowed


def allowed_words(moment: dict) -> set[str]:
    words = _words_in(moment.get("facts", {})) | _words_in([p.get("name", "") for p in moment.get("players", [])])
    return words | ALLOWED_WORDS


def check_text(text: str, moment: dict) -> list[str]:
    """Return the problems found in one piece of text (empty list = grounded)."""
    problems: list[str] = []
    nums = allowed_numbers(moment)
    for raw in NUMBER.findall(text):
        n = float(raw.replace(",", "."))
        if not any(abs(n - a) < 1e-6 for a in nums):
            problems.append(f"number {raw} is not in the facts")
    names = allowed_words(moment)
    for m in WORD.finditer(text):
        word = m.group()
        if not word[0].isupper() or SENTENCE_START.search(text[: m.start()]):
            continue
        base = re.sub(r"['’]s?$", "", word).lower()
        if base not in names:
            problems.append(f"name '{word}' is not in the facts")
    return problems


def check_texts(texts: list[str], moment: dict) -> list[str]:
    seen: list[str] = []
    for t in texts:
        for p in check_text(t, moment):
            if p not in seen:
                seen.append(p)
    return seen
