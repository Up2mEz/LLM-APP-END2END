from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .agent import PROMPT_VERSION, SYSTEM_PROMPT, SEARCH_SYSTEM_PROMPT, VERIFY_SYSTEM_PROMPT
from .config import ROOT, Settings
from .retrieval import file_hash


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evaluate_frozen():
    from ncdqa.retrieval.evaluate import aggregate, score_question
    questions = rows(ROOT / "data/gold/questions_all_reviewed.jsonl")
    parents = {r["chunk_id"]: r for r in rows(ROOT / "data/index/chunks-v12-t512/chunks.jsonl")}
    metrics = {}
    for split in ("dev", "test"):
        gold = {q["qid"]: q for q in questions if q["split"] == split and q["status"] == "gold"}
        for variant in ("A", "B", "C"):
            folder = ROOT / f"data/frozen/{split}-{variant}"
            manifest = json.loads((folder / "run_manifest.json").read_text())
            for path, field in ((folder / "results.jsonl", "results_sha256"),
                                (ROOT / "data/gold/questions_all_reviewed.jsonl", "questions_sha256"),
                                (ROOT / "data/index/chunks-v12-t512/chunks.jsonl", "chunks_sha256")):
                if file_hash(path) != manifest[field]:
                    raise ValueError(f"Frozen run integrity failed: {split}-{variant} {field}")
            predictions = rows(folder / "results.jsonl")
            if len(predictions) != len(gold) or {r["qid"] for r in predictions} != set(gold):
                raise ValueError("Frozen run question set mismatch")
            per_question = {r["qid"]: score_question([parents[h["chunk_id"]] for h in r["hits"]],
                                                    gold[r["qid"]]["evidence"], (1, 3, 5, 10))
                            for r in predictions if gold[r["qid"]]["answerable"]}
            calculated = aggregate(per_question)
            recorded = json.loads((folder / "metrics.json").read_text())["overall"]
            if calculated != recorded:
                raise ValueError(f"Metric mismatch: {split}-{variant}")
            metrics[f"{split}-{variant}"] = {"questions": len(gold), "answerable_denominator": len(per_question),
                                             **calculated, "matches_frozen_metrics": True,
                                             "results_sha256": manifest["results_sha256"]}
    report = {"method": "recomputed_from_saved_ranked_hits; retrieval was not rerun",
              "corpus": "normalized-v12", "baseline": "A dense parent-child", "application_retriever": "B hybrid parent-child",
              "gold_sha256": file_hash(ROOT / "data/gold/questions_all_reviewed.jsonl"), "runs": metrics,
              "test_B_minus_A": {k: round(metrics["test-B"][k] - metrics["test-A"][k], 4) for k in ("recall@5", "mrr@10")},
              "limitations": ["Test was already exposed in the original frozen experiment.",
                              "These are retrieval metrics, not Gemma answer accuracy.",
                              "The runtime agent may choose different queries; that workflow is evaluated separately."]}
    write_json(ROOT / "reports/retrieval_metrics.json", report)
    return report


def make_dev_plan(limit=30):
    if limit < 1 or limit > 30:
        raise ValueError("Development evaluation budget is 1..30 questions")
    gold = [q for q in rows(ROOT / "data/gold/questions_all_reviewed.jsonl") if q["status"] == "gold" and q["split"] == "dev"]
    buckets = defaultdict(list)
    for q in gold:
        buckets[q["type"]].append(q)
    for values in buckets.values():
        values.sort(key=lambda q: hashlib.sha256(("ncd-gemma-dev-v1:" + q["qid"]).encode()).hexdigest())
    selected = []
    while len(selected) < limit:
        for kind in sorted(buckets):
            if buckets[kind] and len(selected) < limit:
                selected.append(buckets[kind].pop(0))
    plan = {"id": "gemma-dev-v13", "split": "dev", "scope": "development evaluation, not a held-out test",
            "qids": [q["qid"] for q in selected], "type_counts": dict(Counter(q["type"] for q in selected)),
            "question_hash": file_hash(ROOT / "data/gold/questions_all_reviewed.jsonl"),
            "prompt_version": PROMPT_VERSION, "prompt_sha256": hashlib.sha256((SEARCH_SYSTEM_PROMPT + SYSTEM_PROMPT + VERIFY_SYSTEM_PROMPT).encode()).hexdigest(),
            "model": "gemma-4-E4B-it", "selection": "round-robin types; SHA256(ncd-gemma-dev-v1:qid) order",
            "temperature": 0, "maximum_model_requests": limit * Settings.from_env().max_steps * 2,
            "maximum_model_rounds": limit * Settings.from_env().max_steps,
            "http_429_retry_limit": 1,
            "max_steps": Settings.from_env().max_steps,
            "table_context_sha256": (file_hash(ROOT / "data/table_context/tables.jsonl")
                                     if (ROOT / "data/table_context/tables.jsonl").is_file() else None),
            "metrics": ["completion rate", "abstention decision accuracy", "citation primary-evidence coverage", "character F1 (lexical proxy only)"],
            "frozen_at_utc": datetime.now(timezone.utc).isoformat()}
    plan["implementation_sha256"] = {
        name: file_hash(Path(__file__).parent / name)
        for name in ("agent.py", "verification.py", "evidence.py", "pdf_tables.py", "json_protocol.py", "question_scope.py", "llm.py", "schemas.py", "config.py", "retrieval.py")
    }
    path = ROOT / "reports/gemma_dev_plan.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        for key in ("id", "qids", "question_hash", "prompt_sha256", "prompt_version", "model", "implementation_sha256", "max_steps", "table_context_sha256"):
            if previous.get(key) != plan[key]:
                raise ValueError("Existing plan differs; create a new version explicitly before evaluating")
        plan = previous
    else:
        write_json(path, plan)
    return selected, plan


def char_f1(predicted, expected):
    from ncd_gemma.agent import collapsed
    import re
    a = Counter(collapsed(re.sub(r"\[S\d+\]", "", predicted)).casefold())
    b = Counter(collapsed(expected or "").casefold())
    common = sum((a & b).values())
    return 2 * common / (sum(a.values()) + sum(b.values())) if a or b else 1.0


def evaluate_agent(agent, limit=30):
    from ncdqa.retrieval.evaluate import covers
    selected, plan = make_dev_plan(limit)
    folder = ROOT / f"private/runs/{plan['id']}"
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "answers.jsonl"
    completed = {r["qid"]: r for r in rows(output)} if output.exists() else {}
    if not set(completed) <= set(plan["qids"]):
        raise ValueError("Saved answers do not belong to evaluation plan")
    if any(r["prediction"].get("prompt_version") != plan["prompt_version"] for r in completed.values()):
        raise ValueError("Saved answers belong to a different agent version")
    for i, q in enumerate(selected, 1):
        if q["qid"] not in completed:
            prediction = agent.run(q["question"])
            record = {"qid": q["qid"], "question": q["question"], "prediction": prediction,
                      "reference_answer": q["answer"], "answerable": q["answerable"]}
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            completed[q["qid"]] = record
        print(json.dumps({"progress": f"{i}/{len(selected)}", "qid": q["qid"],
                          "status": completed[q["qid"]]["prediction"]["status"]}), flush=True)
    evidence_hits, lexical, decisions, stop_reasons, statuses = [], [], [], Counter(), Counter()
    total_api_calls = 0
    for q in selected:
        p = completed[q["qid"]]["prediction"]
        statuses[p["status"]] += 1
        stop_reasons[p["stop_reason"]] += 1
        total_api_calls += p["stats"]["api_calls"]
        decisions.append(p["status"] != "error" and ((p["status"] == "answered") == q["answerable"]))
        if q["answerable"]:
            cited = {c["source_id"] for c in p["citations"]}
            evidence_hits.append(float(any(covers(s, e) for s in p["sources"] if s["source_id"] in cited for e in q["evidence"])))
            lexical.append(char_f1(p["answer"], q["answer"]) if p["status"] == "answered" else 0.0)
    n = len(selected)
    report = {"plan_id": plan["id"], "split": "dev", "n": n, "answerable": len(lexical),
              "status_counts": dict(statuses), "stop_reasons": dict(stop_reasons),
              "completed_rate": round(stop_reasons["completed"] / n, 4),
              "abstention_decision_accuracy": round(sum(decisions) / n, 4),
              "citation_primary_evidence_hit_rate_answerable": round(sum(evidence_hits) / len(evidence_hits), 4) if evidence_hits else None,
              "mean_character_f1_answerable": round(sum(lexical) / len(lexical), 4) if lexical else None,
              "new_api_calls_recorded": total_api_calls,
              "limitations": ["Development sample, not held-out validation.", "Character F1 measures text overlap, not clinical correctness.",
                              "Citation page/quote validity does not prove that every generated claim is entailed.",
                              "Primary evidence metric can miss valid alternative pages.", "Human answer review is still required."]}
    write_json(ROOT / "reports/gemma_dev_metrics.json", report)
    return report
