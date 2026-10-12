"""Record semantic review of the exposed extra-dev-v29 regression.

Only the three changed answers require new judgments. Every other answer,
status, and citation must match the manually reviewed v28 run exactly.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/extra_dev_v28_semantic_audit.json"
PREVIOUS = ROOT / "private/runs/extra-dev-v28/answers.jsonl"
RUN = ROOT / "private/runs/extra-dev-v29/answers.jsonl"
PLAN = ROOT / "reports/extra_dev_v29_plan.json"

OVERRIDES = {
    "q006": ("correct", "ตารางสาเหตุ secondary MCD มีแถว Infection ระบุ Virus และ parasites; citation คัดทั้งหัวตารางและแถวจริง"),
    "q107": ("correct", "ตอบ conventional intermittent สำหรับไหลเวียนคงที่และ SLED สำหรับความดันค่อนข้างต่ำ พร้อมอ้างสองข้อความในเอกสาร edition เดียวกัน"),
    "q110": ("correct", "อ่านข้าวขาว 1 ทัพพีต่อ 1 คาร์บ และโคล่า 1 กระป๋อง 1.7 คาร์บจากข้อความที่อ้างจริง"),
}


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    raw = RUN.read_bytes()
    rows = load_rows(RUN)
    old = {r["qid"]: r for r in load_rows(PREVIOUS)}
    current = {r["qid"]: r for r in rows}
    previous = {d["qid"]: d for d in base["details"]}
    if len(rows) != len(current) or list(current) != plan["qids"] or set(previous) != set(current):
        raise ValueError("Audit must match both complete locked runs")
    changed = [qid for qid in plan["qids"] if any(
        old[qid]["prediction"][key] != current[qid]["prediction"][key]
        for key in ("answer", "status", "citations"))]
    if set(changed) != set(OVERRIDES):
        raise ValueError(f"Unexpected changed answers: {changed}")
    details = []
    for qid in plan["qids"]:
        row = current[qid]
        verdict, note = OVERRIDES.get(qid, (previous[qid]["verdict"], previous[qid]["note"]))
        status = row["prediction"]["status"]
        if (verdict in {"correct", "wrong", "partial", "answered_unanswerable"}) != (status == "answered"):
            raise ValueError(f"Verdict/status mismatch: {qid}")
        details.append({"qid": qid, "type": row["type"], "answerable": row["answerable"],
                        "status": status, "verdict": verdict, "note": note,
                        "cited_documents": sorted({c["document_id"] for c in row["prediction"]["citations"]})})
    counts = Counter(d["verdict"] for d in details)
    strict = {"correct", "correct_abstention"}
    improved = [d["qid"] for d in details if d["verdict"] in strict and previous[d["qid"]]["verdict"] not in strict]
    regressed = [d["qid"] for d in details if d["verdict"] not in strict and previous[d["qid"]]["verdict"] in strict]
    report = {"plan_id": plan["id"], "comparison": base["plan_id"],
              "raw_answers_sha256": hashlib.sha256(raw).hexdigest(), "n": len(details),
              "verdict_counts": dict(counts), "strict_correct": counts["correct"] + counts["correct_abstention"],
              "strict_correct_rate": round((counts["correct"] + counts["correct_abstention"]) / len(details), 4),
              "strict_improved_qids": improved, "strict_regressed_qids": regressed,
              "strict_net_gain": len(improved) - len(regressed), "changed_qids": changed,
              "new_api_calls_recorded": sum(row["prediction"]["stats"]["api_calls"] for row in rows),
              "review_basis": "Coding-agent semantic review of changed answers and their citations; inherited verdicts require byte-identical answers/status/citations from the reviewed v28 run. Exposed dev, not blinded clinical review.",
              "details": details}
    (ROOT / "reports/extra_dev_v29_semantic_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n", "verdict_counts", "strict_correct", "strict_net_gain", "new_api_calls_recorded")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
