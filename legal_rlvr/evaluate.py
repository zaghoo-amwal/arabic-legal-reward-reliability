"""Grade every candidate for every task and write results/scores.json + results/report.md.

Candidates:
  reference          tasks/<id>/reference.md (example answer, not ground truth)
  fixture:<name>     tests/fixtures/<id>__<name>.md (synthetic negative controls)
  run:<label>        runs/<label>/<id>.md (policy outputs from run_policy)
  floor:prompt_echo  the task prompt pasted back as the answer. Its reward is the floor:
                     what a policy earns for restating the brief. Read scores as lift over it.

A task where a plain run already scores >= LOW_SIGNAL is flagged: an RL policy
gets little gradient from it until the rubric is hardened.

    python3 -m legal_rlvr.evaluate            # rules only, no API needed
    python3 -m legal_rlvr.evaluate --judge    # adds AI-judge items (needs API access)
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .env import ROOT, grade, list_tasks, load_task

LOW_SIGNAL = 0.9


def candidates(task_id: str):
    task, _, ref = load_task(task_id)
    yield "reference", ref
    yield "floor:prompt_echo", task["prompt"]
    for f in sorted((ROOT / "tests" / "fixtures").glob(f"{task_id}__*.md")):
        yield f"fixture:{f.stem.split('__', 1)[1]}", f.read_text(encoding="utf-8")
    runs = ROOT / "runs"
    for d in sorted(p for p in runs.iterdir() if p.is_dir()) if runs.exists() else []:
        f = d / f"{task_id}.md"
        if f.exists():
            yield f"run:{d.name}", f.read_text(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--judge-model", default=None)
    args = ap.parse_args()

    all_results = defaultdict(dict)
    for tid in list_tasks():
        for name, text in candidates(tid):
            all_results[tid][name] = grade(tid, text, use_judge=args.judge, judge_model=args.judge_model).to_dict()

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "scores.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render(all_results, args.judge), encoding="utf-8")
    print(render(all_results, args.judge))


def _fmt(s):
    return "—" if s is None else f"{s:.2f}"


def render(res, judged: bool) -> str:
    lines = ["# Legal RLVR: evaluation report", "",
             f"Mode: {'rules + AI judge' if judged else 'rules only (judge items excluded)'}", "",
             "## Reward by task and candidate", "",
             "| Task | Candidate | Reward | Base | Gate |", "|---|---|---|---|---|"]
    for tid, cands in res.items():
        for name, r in cands.items():
            lines.append(f"| {tid} | {name} | **{r['reward']:.2f}** | {r['base_score']:.2f} | ×{r['gate_factor']:.2f} |")
    lines += ["", "## Signal check", "",
              "| Task | Echo floor | Best plain run | Reference | Flag |", "|---|---|---|---|---|"]
    for tid, cands in res.items():
        floor = cands.get("floor:prompt_echo", {}).get("reward")
        runs = [r["reward"] for n, r in cands.items() if n.startswith("run:")]
        best = max(runs) if runs else None
        flag = "low signal" if best is not None and best >= LOW_SIGNAL else ""
        lines.append(f"| {tid} | {_fmt(floor)} | {_fmt(best)} | {cands['reference']['reward']:.2f} | {flag} |")
    lines += ["", "## Item-level detail", ""]
    for tid, cands in res.items():
        names = list(cands)
        lines += [f"### {tid}", "", "| Item | Cat. | W | " + " | ".join(names) + " |",
                  "|---|---|---|" + "---|" * len(names)]
        for i, it in enumerate(cands[names[0]]["items"]):
            row = [cands[n]["items"][i]["score"] for n in names]
            gate = " ⛔" if it.get("gate_multiplier") else ""
            lines.append(f"| {it['id']}{gate} | {it['category']} | {it['weight']} | " + " | ".join(_fmt(s) for s in row) + " |")
        lines.append("")
        for n in names:
            fails = [it for it in cands[n]["items"] if it["score"] is not None and it["score"] < 1]
            if fails:
                lines.append(f"**{n}** misses:")
                lines += [f"- `{it['id']}` ({_fmt(it['score'])}): {it['evidence'][:160]}" for it in fails]
                lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
