"""Generate policy responses (the 'baseline' = plain Claude, no retrieval) for every task.

    python3 -m legal_rlvr.run_policy --model claude-opus-5-5
    python3 -m legal_rlvr.run_policy --model claude-sonnet-5-5 --system prompts/grounded.txt

Writes runs/<label>/<task_id>.md, which `legal_rlvr.evaluate` then grades.
Needs `pip install anthropic` and credentials (ANTHROPIC_API_KEY).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .env import ROOT, list_tasks, load_task


def generate(prompt: str, model: str, effort: str, system: str | None) -> str:
    from .client import make_client

    client = make_client()
    kwargs = dict(
        model=model,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort},
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    with client.beta.messages.stream(**kwargs) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"refused: {msg.stop_details}")
    return "".join(b.text for b in msg.content if b.type == "text")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--system", help="optional system-prompt file (e.g. a grounded/RAG policy)")
    ap.add_argument("--label", help="run folder name (default: model id)")
    ap.add_argument("--tasks", nargs="*", default=None)
    args = ap.parse_args()

    system = Path(args.system).read_text(encoding="utf-8") if args.system else None
    out_dir = ROOT / "runs" / (args.label or args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    for tid in args.tasks or list_tasks():
        task, _, _ = load_task(tid)
        print(f"→ {tid} ({args.model}, effort={args.effort})", flush=True)
        text = generate(task["prompt"], args.model, args.effort, system)
        (out_dir / f"{tid}.md").write_text(text, encoding="utf-8")
    print(f"done → {out_dir}")


if __name__ == "__main__":
    main()
