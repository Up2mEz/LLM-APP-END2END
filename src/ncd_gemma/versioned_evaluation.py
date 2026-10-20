"""Immutable evaluations of the fixed, already exposed development sets.

Gold is joined only by this local harness. Agent.run receives the question alone.
Historical plans and predictions are never rewritten to fit a new implementation.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT, Settings
from .evaluation import char_f1, rows, write_json
from .agent import PROMPT_VERSION, SEARCH_SYSTEM_PROMPT, SYSTEM_PROMPT, VERIFY_SYSTEM_PROMPT
from .retrieval import file_hash

DEFAULT_VERSION = "v31"
QUOTAS = {"number_unit": 7, "condition": 6, "fact": 6, "table": 5,
          "unanswerable": 4, "multi_page": 2}
SCOPE = "Exposed development regression; not held-out or independent clinical validation."


def artifact_path(version: str, suite: str, kind: str) -> Path:
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("Version must be v followed by a positive integer")
    if suite not in ("dev", "extra") or kind not in ("plan", "metrics", "semantic_audit"):
        raise ValueError("Unsupported evaluation artifact")
    return ROOT / "reports/evaluations" / version / f"{suite}_{kind}.json"


def select_questions(limit: int, suite: str) -> list[dict]:
    if not 1 <= limit <= 30:
        raise ValueError("Development evaluation budget is 1..30 questions")
    gold = [q for q in rows(ROOT / "data/gold/questions_all_reviewed.jsonl")
            if q["status"] == "gold" and q["split"] == "dev"]
    buckets = defaultdict(list)
    for q in gold:
        buckets[q["type"]].append(q)
    for values in buckets.values():
        values.sort(key=lambda q: hashlib.sha256(("ncd-gemma-dev-v1:" + q["qid"]).encode()).hexdigest())
    original = []
    while len(original) < 30 and any(buckets.values()):
        for kind in sorted(buckets):
            if buckets[kind] and len(original) < 30:
                original.append(buckets[kind].pop(0))
    if suite == "dev":
        if len(original) < limit:
            raise ValueError("Not enough dev questions")
        return original[:limit]
    if suite != "extra" or limit != 30:
        raise ValueError("The extra-dev regression requires the locked 30 questions")
    used = {q["qid"] for q in original}
    selected = []
    for kind, amount in QUOTAS.items():
        candidates = sorted((q for q in gold if q["type"] == kind and q["qid"] not in used),
                            key=lambda q: hashlib.sha256(("extra-dev-v25:" + q["qid"]).encode()).hexdigest())
        if len(candidates) < amount:
            raise ValueError(f"Not enough extra-dev {kind} questions")
        selected.extend(candidates[:amount])
    return selected


def evaluation_settings(plan: dict) -> Settings:
    settings = Settings.from_env()
    if plan["cache_mode"] == "isolated":
        settings = replace(settings, cache_dir=ROOT / ".cache/evaluations" / plan["id"])
    return settings


def _data_hashes() -> dict:
    manifest_path = ROOT / "provenance/public_data_release.json"
    if not manifest_path.is_file():
        raise ValueError("Public data release manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = {}
    for record in manifest["files"]:
        path = (ROOT / record["path"]).resolve()
        if not path.is_relative_to((ROOT / "data").resolve()):
            raise ValueError("Data manifest path escapes the data directory")
        digest = file_hash(path)
        if digest != record["sha256"]:
            raise ValueError(f"Data differs from public release: {record['path']}")
        result[record["path"]] = digest
    return result


def make_plan(limit=30, version=DEFAULT_VERSION, suite="dev", cache_mode="isolated"):
    path = artifact_path(version, suite, "plan")
    if int(version[1:]) <= 30:
        raise ValueError("v30 and earlier are historical locks; select a new evaluation version")
    if cache_mode not in ("isolated", "shared"):
        raise ValueError("Cache mode must be isolated or shared")
    selected = select_questions(limit, suite)
    gold_hash = file_hash(ROOT / "data/gold/questions_all_reviewed.jsonl")
    # Prevent accidental sample drift relative to the requested v30 comparison.
    baseline_path = (ROOT / "reports/history/v30_gemma_dev_plan.json" if suite == "dev"
                     else ROOT / "reports/extra_dev_v30_plan.json")
    if not baseline_path.is_file() and suite == "dev":
        baseline_path = ROOT / "reports/gemma_dev_plan.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline["id"] != ("gemma-dev-v30" if suite == "dev" else "extra-dev-v30"):
        raise ValueError("The v30 baseline is missing")
    if [q["qid"] for q in selected] != baseline["qids"][:limit]:
        raise ValueError("Question selection differs from the v30 baseline")
    if gold_hash != baseline.get("question_hash", baseline.get("gold_sha256")):
        raise ValueError("Gold differs from the v30 baseline")
    settings = asdict(Settings.from_env())
    settings.pop("cache_dir")
    code = Path(__file__).parent
    implementation = {p.name: file_hash(p) for p in sorted(code.glob("*.py"))}
    reused = {p.relative_to(code.parent).as_posix(): file_hash(p)
              for p in sorted((code.parent / "ncdqa").rglob("*.py"))}
    configs = {p.relative_to(ROOT).as_posix(): file_hash(p)
               for folder in ("configs", "schemas") for p in sorted((ROOT / folder).rglob("*")) if p.is_file()}
    plan = {
        "schema_version": 2, "id": f"{'gemma' if suite == 'dev' else 'extra'}-dev-{version}",
        "evaluation_version": version, "suite": suite, "split": "dev", "scope": SCOPE,
        "qids": [q["qid"] for q in selected], "type_counts": dict(Counter(q["type"] for q in selected)),
        "question_hash": gold_hash, "gold_sha256": gold_hash,
        "baseline_id": baseline["id"], "baseline_plan_sha256": file_hash(baseline_path),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256((SEARCH_SYSTEM_PROMPT + SYSTEM_PROMPT + VERIFY_SYSTEM_PROMPT).encode()).hexdigest(),
        "model": settings["model"], "temperature": 0, "settings": settings,
        "max_steps": settings["max_steps"], "maximum_model_requests": limit * settings["max_steps"] * 2,
        "cache_mode": cache_mode,
        "cache_policy": ("New per-plan cache, empty at first run; reuse only requests from this run on resume."
                         if cache_mode == "isolated" else "Shared response cache; not fresh generation."),
        "implementation_sha256": implementation, "reused_implementation_sha256": reused,
        "configuration_sha256": configs, "data_sha256": _data_hashes(),
        "table_context_sha256": file_hash(ROOT / "data/table_context/tables.jsonl"),
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        changed = [k for k in set(plan) | set(previous)
                   if k != "frozen_at_utc" and previous.get(k) != plan.get(k)]
        if changed:
            raise ValueError(f"Existing plan differs ({', '.join(sorted(changed))}); create a new evaluation version")
        return selected, previous
    write_json(path, plan)
    return selected, plan


def run_locked(agent, selected, plan):
    """Checkpoint every response; reject changed code, data, settings or resume rows."""
    from ncdqa.retrieval.evaluate import covers

    _, verified = make_plan(len(selected), plan["evaluation_version"], plan["suite"], plan["cache_mode"])
    if verified != plan or agent.settings != evaluation_settings(plan):
        raise ValueError("Agent settings or plan differ from the frozen evaluation")
    folder = ROOT / "private/runs" / plan["id"]
    folder.mkdir(parents=True, exist_ok=True)
    output, identity_path = folder / "answers.jsonl", folder / "run_identity.json"
    identity = {"plan_sha256": file_hash(artifact_path(plan["evaluation_version"], plan["suite"], "plan")),
                "cache_mode": plan["cache_mode"], "id": plan["id"]}
    if identity_path.exists():
        if json.loads(identity_path.read_text(encoding="utf-8")) != identity:
            raise ValueError("Saved run identity differs from the frozen plan")
    else:
        if output.exists():
            raise ValueError("Saved answers lack a run identity")
        cache = evaluation_settings(plan).cache_dir
        if plan["cache_mode"] == "isolated" and cache.exists() and any(cache.iterdir()):
            raise ValueError("An isolated evaluation must start with an empty cache")
        write_json(identity_path, identity)
    saved = rows(output) if output.exists() else []
    completed = {r["qid"]: r for r in saved}
    expected = {q["qid"]: q for q in selected}
    if len(saved) != len(completed) or not set(completed) <= set(expected):
        raise ValueError("Duplicate or foreign saved answers")
    for qid, record in completed.items():
        q = expected[qid]
        if (record.get("question"), record.get("reference_answer"), record.get("answerable"),
                record.get("plan_sha256"), record["prediction"].get("prompt_version")) != (
                q["question"], q["answer"], q["answerable"], identity["plan_sha256"], plan["prompt_version"]):
            raise ValueError(f"Saved answer identity changed: {qid}")
    for i, q in enumerate(selected, 1):
        if q["qid"] not in completed:
            # No reference answer, gold evidence or label enters the runtime agent.
            prediction = agent.run(q["question"])
            if prediction.get("prompt_version") != plan["prompt_version"]:
                raise ValueError("Prediction prompt version differs from the plan")
            record = {"qid": q["qid"], "question": q["question"], "prediction": prediction,
                      "reference_answer": q["answer"], "answerable": q["answerable"], "type": q["type"],
                      "plan_sha256": identity["plan_sha256"]}
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            completed[q["qid"]] = record
        print(json.dumps({"suite": plan["suite"], "progress": f"{i}/{len(selected)}", "qid": q["qid"],
                          "status": completed[q["qid"]]["prediction"]["status"]}), flush=True)
    # A file edit while the model was running must also invalidate the run.
    make_plan(len(selected), plan["evaluation_version"], plan["suite"], plan["cache_mode"])
    predictions = [completed[q["qid"]]["prediction"] for q in selected]
    decisions = [p["status"] != "error" and ((p["status"] == "answered") == q["answerable"])
                 for q, p in zip(selected, predictions, strict=True)]
    hits, lexical = [], []
    for q, p in zip(selected, predictions, strict=True):
        if q["answerable"]:
            cited = {c["source_id"] for c in p["citations"]}
            hits.append(float(any(covers(s, e) for s in p["sources"] if s["source_id"] in cited for e in q["evidence"])))
            lexical.append(char_f1(p["answer"], q["answer"]) if p["status"] == "answered" else 0.0)
    n = len(selected)
    stops = Counter(p["stop_reason"] for p in predictions)
    report = {
        "plan_id": plan["id"], "split": "dev", "n": n, "answerable": len(lexical),
        "plan_sha256": identity["plan_sha256"], "answers_sha256": file_hash(output),
        "status_counts": dict(Counter(p["status"] for p in predictions)), "stop_reasons": dict(stops),
        "completed_rate": round(stops["completed"] / n, 4),
        "abstention_decision_accuracy": round(sum(decisions) / n, 4),
        "decision_accuracy": round(sum(decisions) / n, 4),
        "citation_primary_evidence_hit_rate_answerable": round(sum(hits) / len(hits), 4) if hits else None,
        "mean_character_f1_answerable": round(sum(lexical) / len(lexical), 4) if lexical else None,
        "false_abstentions": [q["qid"] for q, p in zip(selected, predictions) if q["answerable"] and p["status"] == "insufficient_evidence"],
        "answered_unanswerable": [q["qid"] for q, p in zip(selected, predictions) if not q["answerable"] and p["status"] == "answered"],
        "error_qids": [q["qid"] for q, p in zip(selected, predictions) if p["status"] == "error"],
        "new_api_calls_recorded": sum(p["stats"]["api_calls"] for p in predictions),
        "model_rounds_total": sum(p["stats"]["model_rounds"] for p in predictions),
        "reported_tokens_including_cache": sum(p["stats"]["reported_tokens_including_cache"] for p in predictions),
        "elapsed_seconds_total": round(sum(p["stats"]["elapsed_ms"] for p in predictions) / 1000, 3),
        "cache_mode": plan["cache_mode"],
        "limitations": [SCOPE, "Decision accuracy is not semantic correctness; manual evidence review is required.",
                        "Character F1 measures text overlap; citation hit checks primary gold evidence only.",
                        "Fresh calls are not a paired model-quality comparison against v30's cached responses."],
    }
    write_json(artifact_path(plan["evaluation_version"], plan["suite"], "metrics"), report)
    return report
