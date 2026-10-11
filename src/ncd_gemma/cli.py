from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, Settings, load_environment, proxy_ready


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--live", action="store_true")
    doctor.add_argument("--retrieval", action="store_true")
    ask = commands.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--out", default="private/latest-answer.json")
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("kind", choices=["retrieval", "agent", "plan"])
    evaluate.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    load_environment()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("ncd_gemma.server:app", host="127.0.0.1", port=args.port)
        return
    from .evaluation import write_json
    if args.command == "doctor":
        report = {"proxy_configured": proxy_ready(), "model": Settings.from_env().model,
                  "data_present": (ROOT / "data/index/dense-bge-m3-t128-v12/vectors.npy").is_file()}
        if args.retrieval:
            from .retrieval import EvidenceRetriever
            from .schemas import SearchArgs
            retriever = EvidenceRetriever()
            hits = retriever.search(SearchArgs(query="เป้าหมาย HbA1c ในผู้ป่วยเบาหวาน", top_k=3))
            report["retrieval"] = {"hits": len(hits), "chunk_ids": [h["chunk_id"] for h in hits]}
        if args.live:
            from .llm import ProxyClient, ProxyError
            from .schemas import SEARCH_TOOL
            try:
                result = ProxyClient(Settings.from_env()).complete(
                    [{"role": "user", "content": "Call search_docs to search for NCD guideline evidence. Do not answer yet."}],
                    [SEARCH_TOOL], {"type": "function", "function": {"name": "search_docs"}}, 40)
                calls = result["message"].get("tool_calls", [])
                report["proxy_probe"] = {"native_tool_call": any(c["function"]["name"] == "search_docs" for c in calls),
                                          "finish_reason": result["finish_reason"], "cached": result["cached"],
                                          "latency_ms": result["latency_ms"]}
            except ProxyError as exc:
                report["proxy_probe"] = {"error": exc.category}
        suffix = "-proxy" if args.live else "-retrieval" if args.retrieval else ""
        write_json(ROOT / f"reports/doctor{suffix}.json", report)
        print(json.dumps(report))
        if report.get("proxy_probe", {}).get("error"):
            raise SystemExit(1)
        return
    if args.command == "evaluate":
        from .evaluation import evaluate_frozen, make_dev_plan
        if args.kind == "retrieval":
            result = evaluate_frozen()
            print(json.dumps({"runs_verified": len(result["runs"]), "test_B_minus_A": result["test_B_minus_A"]}))
            return
        if args.kind == "plan":
            _, plan = make_dev_plan(args.limit)
            print(json.dumps(plan))
            return
    from .server import get_agent
    agent = get_agent()
    if args.command == "ask":
        result = agent.run(args.question)
        output = (ROOT / args.out).resolve()
        if not output.is_relative_to(ROOT):
            raise ValueError("Output must stay within this project")
        write_json(output, result)
        print(json.dumps({"output": str(output), "status": result["status"], "stop_reason": result["stop_reason"], "stats": result["stats"]}))
    else:
        from .evaluation import evaluate_agent
        print(json.dumps(evaluate_agent(agent, args.limit)))


if __name__ == "__main__":
    main()
