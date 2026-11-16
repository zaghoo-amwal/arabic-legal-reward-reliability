"""Second-judge crosscheck: does the judge favour answers written by its own model?

    python3 -m legal_rlvr.crosscheck --second claude-sonnet-5-5

Re-scores every judge item for the reference, the plain-Claude runs and the
negative controls with a second judge model, and compares it to the primary
judge. If the primary judge (same family as the policy) rates the policy's
answers higher than the second judge does, *more* than it does for the
reference, that difference is a self-preference estimate.
Writes results/judge_crosscheck.json. Both judges use the cache.
"""
from __future__ import annotations

import argparse
import json

from .env import ROOT, list_tasks, load_task
from .evaluate import candidates
from .judge import JUDGE_MODEL, cached_judge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--second", default="claude-sonnet-5-5")
    args = ap.parse_args()

    rows = []
    for tid in list_tasks():
        task, rubric, ref = load_task(tid)
        items = [it for it in rubric["items"] if it["check"]["type"] == "judge"]
        for name, text in candidates(tid):
            if name.startswith("floor:"):
                continue
            a = cached_judge(task, items, text, ref, JUDGE_MODEL)
            b = cached_judge(task, items, text, ref, args.second)
            for it in items:
                rows.append({"task": tid, "candidate": name, "item": it["id"],
                             "primary": a[it["id"]][0], "second": b[it["id"]][0]})

    def mean_gap(pred):
        sel = [r["primary"] - r["second"] for r in rows if pred(r)]
        return round(sum(sel) / len(sel), 3) if sel else None

    summary = {
        "primary_judge": JUDGE_MODEL, "second_judge": args.second,
        "gap_on_runs": mean_gap(lambda r: r["candidate"].startswith("run:")),
        "gap_on_reference": mean_gap(lambda r: r["candidate"] == "reference"),
        "gap_on_fixtures": mean_gap(lambda r: r["candidate"].startswith("fixture:")),
        "agreement": round(sum(r["primary"] == r["second"] for r in rows) / len(rows), 3),
    }
    if summary["gap_on_runs"] is not None and summary["gap_on_reference"] is not None:
        summary["self_preference_estimate"] = round(summary["gap_on_runs"] - summary["gap_on_reference"], 3)
    out = ROOT / "results" / "judge_crosscheck.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows:
        if r["primary"] != r["second"]:
            print(f"  {r['task']:28s} {r['candidate']:24s} {r['item']:32s} primary={r['primary']} second={r['second']}")


if __name__ == "__main__":
    main()
