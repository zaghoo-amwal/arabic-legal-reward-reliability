"""RLVR environment: task loading, grading and reward aggregation.

reward = (sum_i w_i * s_i / sum_i w_i) * prod_{gates failed} gate_multiplier

* s_i in [0, 1] comes from a rule check or the AI judge.
* Gate items (language, the outdated-law trap, no-assumption constraints)
  multiply the whole reward down when failed. A response that is fluent but
  legally wrong on the core point can't score well on breadth alone.
* Without the judge, judge items are left out and the result is marked rules_only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .checks import CHECKS
from .normalize import normalize

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"


def list_tasks() -> list[str]:
    return sorted(p.name for p in TASKS_DIR.iterdir() if (p / "task.json").exists())


def load_task(task_id: str) -> tuple[dict, dict, str]:
    d = TASKS_DIR / task_id
    task = json.loads((d / "task.json").read_text(encoding="utf-8"))
    rubric = json.loads((d / "rubric.json").read_text(encoding="utf-8"))
    reference = (d / task["reference"]["path"]).read_text(encoding="utf-8")
    return task, rubric, reference


@dataclass
class GradeResult:
    task_id: str
    reward: float
    rules_only: bool
    base_score: float
    gate_factor: float
    items: list[dict] = field(default_factory=list)

    def to_dict(self):
        return self.__dict__


def grade(task_id: str, response: str, use_judge: bool = False, judge_model: str | None = None) -> GradeResult:
    task, rubric, reference = load_task(task_id)
    norm = normalize(response)
    results = []
    judge_items = [it for it in rubric["items"] if it["check"]["type"] == "judge"]

    judged = {}
    if use_judge and judge_items:
        from .judge import JUDGE_MODEL, cached_judge
        judged = cached_judge(task, judge_items, response, reference, judge_model or JUDGE_MODEL)

    for it in rubric["items"]:
        ctype = it["check"]["type"]
        if ctype == "judge":
            if it["id"] not in judged:
                results.append({**_meta(it), "score": None, "evidence": "judge not run"})
                continue
            score, ev = judged[it["id"]]
        else:
            score, ev = CHECKS[ctype](it["check"], norm, response)
        results.append({**_meta(it), "score": round(score, 3), "evidence": ev})

    scored = [r for r in results if r["score"] is not None]
    wsum = sum(r["weight"] for r in scored)
    base = sum(r["weight"] * r["score"] for r in scored) / wsum if wsum else 0.0
    gate = 1.0
    for r in scored:
        if r.get("gate_multiplier") and r["score"] < 1.0:
            gate *= r["gate_multiplier"]
    return GradeResult(task_id, round(base * gate, 4), len(scored) < len(results), round(base, 4), gate, results)


def _meta(it):
    return {k: it.get(k) for k in ("id", "category", "weight", "gate_multiplier", "desc")}


class LegalDraftingEnv:
    """Minimal single-step env interface: reset() -> prompt, step(response) -> (reward, info)."""

    def __init__(self, task_id: str, use_judge: bool = True):
        self.task_id, self.use_judge = task_id, use_judge
        self.task, _, _ = load_task(task_id)

    def reset(self) -> str:
        return self.task["prompt"]

    def step(self, response: str):
        res = grade(self.task_id, response, use_judge=self.use_judge)
        return res.reward, res.to_dict()
