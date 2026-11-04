# Paired agent evaluation implementation plan

> Execute inline with executing-plans. User authorized implementation.

Goal: Compare the recovered v30 agent and current agent on the same 60 exposed development questions with fresh model calls and the same scorer.

Architecture: Recover old files by their recorded SHA-256. Run both implementations in one controlled harness with a shared proxy transport, settings and cache-off policy. Preserve raw outputs and alternate arm order by question. This measures old/current agent behavior under normalized execution controls, not historical service conditions.

Spec: User requests fair old/new evaluation and correct explanation of ReAct versus React.

Global constraints: gemma-4-E4B-it, temperature 0, max_steps 6, searches 3, request timeout 45s, agent timeout 150s, 1400 output tokens, 18000 context characters, 20 sources. Hybrid retrieval and reranker ON. No answer/reranker cache. Gold only in scoring. Preserve HTTP errors in denominator; stop on three consecutive service failures. Up to 120 answer requests, 1440 proxy attempts, 4 hours; do not silently retry unresolved in-flight requests. Judge is Luna xhigh, blinded, same rubric for both arms. Original results remain immutable.

Review focus: unavailable old bytes; unpaired data; cache contamination; outage credit; interruption duplicate requests.

- [x] Recover and verify 18 old runtime files; record normalized control replacements separately.
- [x] Implement separate harness outside frozen current runtime and tests for paired IDs, failure accounting, cache controls and durable resume.
- [x] Run 60 paired questions with alternating order, no replacement results.
- [x] Judge all 120 answers with blinded Luna xhigh and identical rubric; publish paired scores and disagreements.
- [x] Correct ReAct terminology and link current comparison without claiming newer is better; run tests and independent harness review.

Recovery: config.py reconstructed from the recorded Git version by setting max_sources=20, verified byte-for-byte against the v30 SHA-256. No guessed file is accepted without a hash match.
