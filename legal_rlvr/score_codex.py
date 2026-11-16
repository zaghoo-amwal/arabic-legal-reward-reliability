"""Audit and score a Codex run without replacing the existing benchmark report."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from .env import ROOT, grade
from .evaluate import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    parser.add_argument('--judge', action='store_true')
    args = parser.parse_args()
    if Path(args.label).name != args.label:
        parser.error('label must be a single directory name')
    audit = ROOT / 'results' / args.label
    manifest = json.loads((audit / 'manifest.json').read_text())
    # Refuse grading under changed benchmark definitions.
    import hashlib
    for rel, digest in manifest['snapshot_sha256'].items():
        if rel.startswith(('tasks/', 'citations/', 'legal_rlvr/')):
            path = ROOT / rel
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise SystemExit('Benchmark changed since generation: ' + rel)
    results = defaultdict(dict)
    for tid, record in manifest['tasks'].items():
        events = [json.loads(line) for line in (audit / (tid + '.events.jsonl')).read_text().splitlines() if line.strip()]
        tools = [e for e in events if e.get('item', {}).get('type') not in (None, 'error', 'reasoning', 'agent_message')]
        completed = [e for e in events if e.get('type') == 'turn.completed']
        if tools or not completed or record['returncode'] != 0:
            raise SystemExit('Run did not pass no-tools/completion audit: ' + tid)
        record['status'] = 'audited_no_tool_events'
        record['usage'] = completed[-1].get('usage')
        task_dir = audit / 'snapshot' / 'tasks' / tid
        task = json.loads((task_dir / 'task.json').read_text())
        candidates = {'reference': (task_dir / task['reference']['path']).read_text(),
                      'floor:prompt_echo': task['prompt'],
                      'run:' + args.label: (ROOT / 'runs' / args.label / (tid + '.md')).read_text()}
        baseline = ROOT / 'runs' / 'claude-opus-5-5' / (tid + '.md')
        if baseline.exists():
            candidates['run:claude-opus-5-5'] = baseline.read_text()
        for name, text in candidates.items():
            print('Scoring ' + tid + ' / ' + name, flush=True)
            results[tid][name] = grade(tid, text, use_judge=args.judge).to_dict()
        (audit / 'scores.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        (audit / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    suffix = '\n\n## Run conditions\n\nSingle response per task; Codex CLI with requested model ' + manifest['model_requested'] + ', reasoning ' + manifest['effort'] + '. Fresh temporary working directories, no references or rubrics in prompts, tools disabled, and no tool events in the saved transcripts. Codex system instructions still apply; this is not a raw API evaluation. Model identity is requested configuration, not independently attested by the returned text events. References and Claude baseline are saved artifacts.\n'
    (audit / 'report.md').write_text(render(results, args.judge) + suffix)
    print('Report: ' + str(audit / 'report.md'), flush=True)


if __name__ == '__main__':
    main()
