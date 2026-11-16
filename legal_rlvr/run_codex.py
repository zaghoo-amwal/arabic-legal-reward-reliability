"""Run prompt-only Codex evaluations with frozen inputs and auditable events.

Uses the existing Codex login, not the OpenAI API. No references or rubrics
are included in generation prompts. Outputs are compatible with evaluate.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .env import ROOT, list_tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='gpt-6-astra')
    parser.add_argument('--effort', default='high')
    parser.add_argument('--label', default='gpt-6-astra-codex-high-r1')
    parser.add_argument('--tasks', nargs='+')
    args = parser.parse_args()
    if Path(args.label).name != args.label:
        parser.error('label must be a single directory name')
    out = ROOT / 'runs' / args.label
    audit = ROOT / 'results' / args.label
    out.mkdir(parents=True, exist_ok=True)
    audit.mkdir(parents=True, exist_ok=True)
    snapshot = audit / 'snapshot'
    if snapshot.exists():
        parser.error('this run already exists; choose a new label')
    shutil.copytree(ROOT / 'tasks', snapshot / 'tasks')
    shutil.copytree(ROOT / 'citations', snapshot / 'citations')
    shutil.copytree(ROOT / 'legal_rlvr', snapshot / 'legal_rlvr', ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('scores.json', 'report.md', 'judge_cache.json'):
        path = ROOT / 'results' / name
        if path.exists():
            shutil.copy2(path, snapshot / name)
    manifest = {'harness': 'Codex CLI, not raw API', 'model_requested': args.model,
                'effort': args.effort, 'started_at': datetime.now(timezone.utc).isoformat(),
                'tasks': {}, 'snapshot_sha256': {str(p.relative_to(snapshot)): hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in snapshot.rglob('*') if p.is_file()}}
    def save():
        (audit / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    save()
    disabled = ['shell_tool', 'unified_exec', 'apps', 'plugins', 'memories',
                'multi_agent', 'multi_agent_v2', 'browser_use', 'computer_use',
                'image_generation', 'hooks', 'skill_search', 'code_mode', 'code_mode_host']
    for tid in args.tasks or list_tasks():
        task = json.loads((snapshot / 'tasks' / tid / 'task.json').read_text())
        print('Generating ' + tid, flush=True)
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='legal-astra-') as work:
            answer = Path(work) / 'answer.md'
            cmd = ['codex', 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                   '--sandbox', 'read-only', '--model', args.model, '--cd', work,
                   '-c', 'model_reasoning_effort="' + args.effort + '"',
                   '-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0',
                   '-c', 'features.skip_host_skill_discovery=true',
                   '-c', 'developer_instructions="Answer the user task directly in your final response. Do not use tools, inspect files, or create downloadable files. Provide the complete requested content inline."',
                   '--json', '--output-last-message', str(answer)]
            for feature in disabled:
                cmd += ['--disable', feature]
            cmd += ['-']
            with (audit / (tid + '.events.jsonl')).open('w') as events, (audit / (tid + '.stderr.log')).open('w') as errors:
                result = subprocess.run(cmd, input=task['prompt'], text=True, stdout=events, stderr=errors, timeout=900)
            record = {'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 2),
                      'prompt_sha256': hashlib.sha256(task['prompt'].encode()).hexdigest()}
            if result.returncode == 0 and answer.exists() and answer.read_text().strip():
                shutil.copy2(answer, out / (tid + '.md'))
                record['status'] = 'generated_pending_audit'
            else:
                record['status'] = 'failed'
            manifest['tasks'][tid] = record
            save()
            print(tid + ': ' + record['status'], flush=True)
            if record['status'] == 'failed':
                raise SystemExit('Generation failed; see ' + str(audit / (tid + '.stderr.log')))
    print('Outputs: ' + str(out), flush=True)


if __name__ == '__main__':
    main()
