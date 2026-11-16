"""Measure trap false-penalty and miss rates on the frozen matched pairs.

    python3 -m experiments.verifier_validation.measure

Runs offline, without the private task corpus: the six trap definitions are in
trap_specs.json (v1 = before the fix, v2 = after). v1 is scored with a frozen
copy of the original checker, v2 with the current legal_rlvr.checks.trap.
Writes experiments/verifier_validation/measured.json.
"""
import hashlib
import json
import re
from pathlib import Path

from legal_rlvr.checks import _search, trap as trap_v2
from legal_rlvr.normalize import normalize, normalize_pattern

HERE = Path(__file__).parent
# SHA-256 of the pairs as frozen on 2026-11-16 (JSON Lines, one json.dumps(row,
# ensure_ascii=False) per line), recorded before any change to the checker.
# pairs.json is the same rows re-serialised; frozen_hash() rebuilds the original bytes.
FROZEN_SHA256 = "cbd93ce871c86c034241647073e7a8f67f158e32e10bd77c349bcc337f0235b2"


def frozen_hash(rows):
    lines = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def trap_v1(spec, norm, raw):
    """Frozen copy of the trap checker before the fix (2026-11-16)."""
    unless = [normalize_pattern(p) for p in spec.get("unless", [])]
    window = spec.get("excuse_window")
    hits = [m for p in spec["bad"] for m in re.finditer(normalize_pattern(p), norm, flags=re.S)]
    if not hits:
        return 1.0, "not triggered"
    if window is None:
        return (1.0, "excused") if _search(spec.get("unless", []), norm) else (0.0, "TRAP")
    unexcused = [m for m in hits
                 if not any(re.search(u, norm[max(0, m.start() - window): m.end() + window], flags=re.S) for u in unless)]
    return (1.0, "excused") if not unexcused else (0.0, "TRAP")


def load():
    rows = json.loads((HERE / "pairs.json").read_text(encoding="utf-8"))
    specs = json.loads((HERE / "trap_specs.json").read_text(encoding="utf-8"))
    return rows, specs, frozen_hash(rows)


def score(rows, specs, version):
    checker = trap_v1 if version == "v1" else trap_v2
    out = []
    for r in rows:
        spec = specs[f"{r['task']}/{r['trap']}"][version]
        s, _ = checker(spec, normalize(r["text"]), r["text"])
        out.append({**r, "flagged": s == 0.0})
    return out


def metrics(res):
    m = {}
    for split in ("dev", "heldout", "all"):
        sel = [r for r in res if split == "all" or r["split"] == split]
        comp = [r for r in sel if r["label"] == "compliant"]
        viol = [r for r in sel if r["label"] == "violation"]
        fp = sum(r["flagged"] for r in comp)
        fn = sum(not r["flagged"] for r in viol)
        m[split] = {"n": len(sel), "false_penalty": f"{fp}/{len(comp)}", "miss": f"{fn}/{len(viol)}",
                    "accuracy": round(1 - (fp + fn) / len(sel), 3)}
    return m


def main():
    rows, specs, sha = load()
    if sha != FROZEN_SHA256:
        raise SystemExit(f"pairs.json differs from the frozen set (sha256 {sha})")
    report = {"pairs_sha256": sha}
    for v in ("v1", "v2"):
        res = score(rows, specs, v)
        report[v] = {"metrics": metrics(res),
                     "errors": [{k: r[k] for k in ("id", "split", "label", "phenomenon", "text")}
                                for r in res if r["flagged"] != (r["label"] == "violation")]}
    (HERE / "measured.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in ("v1", "v2"):
        for split, m in report[v]["metrics"].items():
            print(f"{v} {split:8s} false penalties {m['false_penalty']:6s} misses {m['miss']:6s} accuracy {m['accuracy']}")


if __name__ == "__main__":
    main()
