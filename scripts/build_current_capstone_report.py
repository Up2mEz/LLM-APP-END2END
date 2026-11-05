"""Render the canonical submission Markdown after checking published metrics.

This command never rewrites the authored report or calls a model.
"""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    folder = ROOT / 'reports/capstone-current-v2'
    metrics = json.loads((folder / 'metrics.json').read_text(encoding='utf-8'))
    judge = json.loads((folder / 'judge_metrics.json').read_text(encoding='utf-8'))
    paired = json.loads((ROOT / 'reports/paired-agent-v30-current-20261105/paired_summary.json').read_text(encoding='utf-8'))
    if not metrics.get('complete') or not judge.get('complete') or paired['n'] != 60:
        raise ValueError('Complete published evidence is required')
    text = (ROOT / 'docs/PROJECT_REPORT_SUBMISSION_TH.md').read_text(encoding='utf-8')
    for arm in ('dense_default', 'hybrid_current'):
        recall = metrics['retrieval'][arm]['recall@5']
        score = f"{judge['arms'][arm]['successes']}/30"
        if f'{recall:.2f}' not in text or score not in text:
            raise ValueError('Report and evaluation numbers disagree')
    for key in ('old_successes', 'current_successes'):
        if f"{paired[key]}/60" not in text:
            raise ValueError('Report and paired result disagree')
    subprocess.run(['node', 'scripts/render_submission_report.mjs'], cwd=ROOT, check=True)

if __name__ == '__main__':
    main()
