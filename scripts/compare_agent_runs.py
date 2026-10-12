"""Compare fixed development runs without relabelling errors or tuning gold."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


active = read(ROOT / "reports/gemma_dev_plan.json")
runs = []
versions = {p.name.split('_')[0] for p in (ROOT/'reports/history').glob('v*_gemma_dev_plan.json')}
versions.add(active['id'].replace('gemma-dev-',''))
partial = []
for version in sorted(versions, key=lambda v:int(v[1:])):
    current = active["id"] == f"gemma-dev-{version}"
    prefix = ROOT / "reports" if current else ROOT / "reports/history"
    stem = "" if current else version + "_"
    plan = read(prefix / (stem + "gemma_dev_plan.json"))
    metrics_path = prefix / (stem + "gemma_dev_metrics.json")
    if not metrics_path.exists():
        receipt = ROOT/'reports/history'/f'{version}_aborted_run.json'
        if receipt.exists():
            partial.append(read(receipt))
            continue
        raise ValueError(f'Missing metrics without an aborted-run receipt: {version}')
    metrics = read(metrics_path)
    if plan["qids"] != active["qids"] or plan["question_hash"] != active["question_hash"]:
        raise ValueError("Question identity differs between runs")
    records = [json.loads(s) for s in (ROOT / f"private/runs/{plan['id']}/answers.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(records) != 30 or {r["qid"] for r in records} != set(active["qids"]):
        raise ValueError("Incomplete or duplicate result set")
    runs.append({**metrics,
        "max_model_calls_per_question": plan.get("max_steps", 4),
        "model_rounds_total": sum(r["prediction"]["stats"]["model_rounds"] for r in records),
        "searches_total": sum(r["prediction"]["stats"]["searches"] for r in records),
        "false_abstentions": [r["qid"] for r in records if r["answerable"] and r["prediction"]["status"] == "insufficient_evidence"],
        "answered_unanswerable": [r["qid"] for r in records if not r["answerable"] and r["prediction"]["status"] == "answered"],
        "correct_abstentions": [r["qid"] for r in records if not r["answerable"] and r["prediction"]["status"] == "insufficient_evidence"]})
report = {"scope": "Same exposed development sample; cached completions reused when payloads match. Not independent validation.",
          "selection": "Report all iterations, including failures. Read the semantic audit alongside these automatic metrics.",
          "runs": runs, 'partial_runs':partial}
(ROOT / "reports/agent_comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"versions": len(runs), "current_false_abstentions": len(runs[-1]["false_abstentions"]),
                  "current_answered_unanswerable": len(runs[-1]["answered_unanswerable"])}))
