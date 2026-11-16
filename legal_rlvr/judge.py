"""AI-judge for rubric items that rules can't check (judgement, constraint-following).

The judge sees the task, the rubric items, the candidate response, and the
reference as *guidance* (not ground truth). It returns a 0/1/2 score per item
with a rationale, using JSON-schema structured output.
"""
from __future__ import annotations

import json

JUDGE_MODEL = "claude-opus-5-5"

SYSTEM = (
    "You are a strict Saudi-law grading assistant for an RL reward model. "
    "Score each rubric item independently for the CANDIDATE response only. "
    "The REFERENCE is a strong example answer from a retrieval-grounded system. Use it as guidance on what good looks like, "
    "but don't penalise correct content that differs from it, and don't reward content because it copies it. "
    "Scores: 2 = clearly satisfied, 1 = partially satisfied, 0 = not satisfied or contradicted. "
    "Quote the candidate's own words (in Arabic) in each rationale."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "integer", "enum": [0, 1, 2]},
                    "rationale": {"type": "string"},
                },
                "required": ["id", "score", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def judge_items(task: dict, items: list[dict], response: str, reference: str, model: str = JUDGE_MODEL) -> dict:
    from .client import make_client  # lazy: rules-only grading needs no SDK

    rubric = "\n".join(f"- id: {it['id']}\n  criterion: {it['desc']}" for it in items)
    user = (
        f"<task_prompt>\n{task['prompt']}\n</task_prompt>\n\n"
        f"<reference kind=\"{task['reference']['kind']}\">\n{reference}\n</reference>\n\n"
        f"<candidate_response>\n{response}\n</candidate_response>\n\n"
        f"<rubric_items>\n{rubric}\n</rubric_items>\n\n"
        "Return one entry per rubric item id."
    )
    client = make_client()
    msg = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"judge refused: {msg.stop_details}")
    text = next(b.text for b in msg.content if b.type == "text")
    out = {r["id"]: r for r in json.loads(text)["items"]}
    return {it["id"]: (out[it["id"]]["score"] / 2, out[it["id"]]["rationale"]) for it in items if it["id"] in out}


# ---- cache: re-grading after rubric/rule changes shouldn't pay for the judge again ----
import hashlib
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "results" / "judge_cache.json"


def cache_key(task_id: str, items: list[dict], response: str, model: str) -> str:
    spec = json.dumps([[it["id"], it["desc"]] for it in items], ensure_ascii=False)
    return hashlib.sha256("\x1f".join([model, task_id, spec, response]).encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    return json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}


def cached_judge(task: dict, items: list[dict], response: str, reference: str, model: str = JUDGE_MODEL) -> dict:
    cache = _load_cache()
    key = cache_key(task["task_id"], items, response, model)
    if key not in cache:
        res = judge_items(task, items, response, reference, model)
        cache = _load_cache()
        cache[key] = {k: list(v) for k, v in res.items()}
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {k: tuple(v) for k, v in cache[key].items()}
