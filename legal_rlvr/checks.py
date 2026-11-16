"""Deterministic (rule-based) rubric checks.

Each check returns (score in [0, 1], evidence string). Evidence is a short
snippet of the normalised response, so every reward is auditable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .normalize import arabic_ratio, normalize_pattern

ROOT = Path(__file__).resolve().parent.parent
LEDGER = json.loads((ROOT / "citations" / "ledger.json").read_text(encoding="utf-8"))
STATUTE_MAX = {normalize_pattern(k): v for k, v in LEDGER["statute_max_article"].items() if not k.startswith("_")}
CASE_RE = re.compile(r"(?<!\d)(\d{8,11}/14\d\d)(?!\d)")


def _snip(text: str, m: re.Match, pad: int = 45) -> str:
    return "…" + text[max(0, m.start() - pad): m.end() + pad].replace("\n", " ") + "…"


def _search(patterns, text):
    for p in patterns:
        m = re.search(normalize_pattern(p), text, flags=re.S)
        if m:
            return m
    return None


def regex_any(spec, norm, raw):
    m = _search(spec["patterns"], norm)
    return (1.0, _snip(norm, m)) if m else (0.0, "no match")


def regex_all(spec, norm, raw):
    hits, ev = 0, []
    for group in spec["groups"]:
        m = _search(group, norm)
        if m:
            hits += 1
            ev.append(_snip(norm, m, 25))
        else:
            ev.append(f"MISSING: {group[0][:40]}")
    n = len(spec["groups"])
    score = hits / n if spec.get("partial") else float(hits == n)
    return score, " | ".join(ev)


def coverage(spec, norm, raw):
    missing = [g[0][:30] for g in spec["groups"] if not _search(g, norm)]
    hits = len(spec["groups"]) - len(missing)
    return min(1.0, hits / spec["min"]), f"{hits}/{len(spec['groups'])} covered" + (f"; missing: {missing}" if missing else "")


def count_min(spec, norm, raw):
    n = len(re.findall(normalize_pattern(spec["pattern"]), norm))
    return min(1.0, n / spec["n"]), f"{n} occurrences (target {spec['n']})"


def trap(spec, norm, raw):
    """Fails if a known-wrong statement appears without an excuse.

    With `excuse_window` (chars), every bad match must have an excuse pattern
    within that distance. One properly framed sentence can't excuse an outdated
    rule restated elsewhere (e.g. in a risk table). Without it, any excuse
    anywhere in the text counts (the original, looser behaviour).
    """
    unless = [normalize_pattern(p) for p in spec.get("unless", [])]
    window = spec.get("excuse_window")
    hits = [m for p in spec["bad"] for m in re.finditer(normalize_pattern(p), norm, flags=re.S)]
    if not hits:
        return 1.0, "trap not triggered"
    if window is None:
        excuse = _search(spec.get("unless", []), norm)
        if excuse:
            return 1.0, f"outdated rule mentioned but framed as superseded: {_snip(norm, excuse, 25)}"
        return 0.0, f"TRAP: {_snip(norm, hits[0])}"
    unexcused = [m for m in hits
                 if not any(re.search(u, norm[max(0, m.start() - window): m.end() + window], flags=re.S) for u in unless)]
    if not unexcused:
        return 1.0, f"{len(hits)} outdated-rule mention(s), all framed as superseded nearby"
    return 0.0, f"TRAP ({len(unexcused)}/{len(hits)} unexcused): {_snip(norm, unexcused[0])}"


def arabic(spec, norm, raw):
    r = arabic_ratio(raw)
    return float(r >= spec["min"]), f"arabic ratio {r:.2f}"


def citation_range(spec, norm, raw):
    """Flags article numbers that exceed the statute's last article."""
    bad = []
    for m in re.finditer(r"الماده (\d+)([^\n]{0,90})", norm):
        num, tail = int(m.group(1)), m.group(2)
        for law, mx in STATUTE_MAX.items():
            i = tail.find(law)
            if i != -1 and "لائحه" not in tail[:i] and "الماده" not in tail[:i]:
                if num > mx:
                    bad.append(f"Art. {num} > {mx} ({law})")
                break
    return (0.0, "; ".join(bad)) if bad else (1.0, "no out-of-range citations")


def case_numbers_allowlist(spec, norm, raw):
    cited = set(CASE_RE.findall(norm))
    unknown = sorted(cited - set(spec["allow"]))
    if unknown:
        return 0.0, f"unverifiable case numbers: {unknown}"
    return 1.0, f"{len(cited)} case numbers cited, all in allowlist" if cited else "no case numbers cited"


CHECKS = {
    "regex_any": regex_any, "regex_all": regex_all, "coverage": coverage,
    "count_min": count_min, "trap": trap, "arabic_ratio": arabic,
    "citation_range": citation_range, "case_numbers_allowlist": case_numbers_allowlist,
}
