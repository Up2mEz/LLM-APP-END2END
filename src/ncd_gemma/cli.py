from __future__ import annotations

import argparse
import json
import sys

from .config import ROOT, Settings, allowed_hosts, load_environment, proxy_ready


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--live", action="store_true")
    doctor.add_argument("--retrieval", action="store_true")
    ask = commands.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--out", default="private/latest-answer.json")
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("kind", choices=["retrieval", "agent", "plan"])
    evaluate.add_argument("--limit", type=int, default=30)
    evaluate.add_argument("--version", default="v31")
    evaluate.add_argument("--suite", choices=["dev", "extra", "both"], default="dev")
    evaluate.add_argument("--cache-mode", choices=["isolated", "shared"], default="isolated")
    args = parser.parse_args()
    load_environment()
    if args.command == "serve":
        import uvicorn
        if args.host == "0.0.0.0" and len(allowed_hosts()) == 3:
            parser.error("Set NCD_PUBLIC_HOST and NCD_DEMO_PASSWORD before binding a remote demo")
        uvicorn.run("ncd_gemma.server:app", host=args.host, port=args.port)
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
        from .evaluation import evaluate_frozen
        if args.kind == "retrieval":
            result = evaluate_frozen()
            print(json.dumps({"runs_verified": len(result["runs"]), "test_B_minus_A": result["test_B_minus_A"]}))
            return
        from .versioned_evaluation import evaluation_settings, make_plan, run_locked
        suites = ("dev", "extra") if args.suite == "both" else (args.suite,)
        plans = [make_plan(args.limit, args.version, suite, args.cache_mode) for suite in suites]
        if args.kind == "plan":
            print(json.dumps([p for _, p in plans]))
            return
        from .agent import Agent
        from .llm import ProxyClient
        from .retrieval import EvidenceRetriever
        retriever = EvidenceRetriever()
        results = []
        for selected, plan in plans:
            settings = evaluation_settings(plan)
            agent = Agent(ProxyClient(settings), retriever, settings)
            results.append(run_locked(agent, selected, plan))
        print(json.dumps(results))
        if any(r["error_qids"] for r in results):
            raise SystemExit(1)
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


if __name__ == "__main__":
    main()
