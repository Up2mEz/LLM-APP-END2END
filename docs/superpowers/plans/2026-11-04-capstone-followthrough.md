# Completion after fresh baseline

User authorized full implementation and GPT-6-Luna xhigh judging after the earlier planning-only gate. Keep the current pipeline frozen until the run finishes. No push, deployment or upload is included.

1. Complete capstone-current-v2, validate all 60 retrieval and 60 answer records, and run blinded Luna judging using the frozen rubric. Preserve service errors and uncertain verdicts.
2. Inspect actual failures before proposing any production fix. Do not tune on judge verdicts and then report the same run as post-fix. A necessary runtime change needs a separately named snapshot and an explicit bounded comparison.
3. Measure a retrieval-only reranker ablation on the same 30 questions: compare the saved fresh hybrid/reranker-ON retrieval arm with 30 new hybrid/reranker-OFF searches under identical code/data. Budget: 30 retrieval calls, zero Gemma calls, 45 minutes. Cache remains OFF. Report this as retrieval quality/latency, not end-to-end answer quality; sequential timings are descriptive.
4. Update README, report and AboutSystem with the new scope/results. Keep the approved UI; apply design contract and skills before each frontend edit. The report remains 4–8 pages, black Thai text, selectable Unicode without overlapping marks, no revision date, and a conclusions/limitations section without promises of future work.
5. Update demo narration and capture with actual evidence, 3–6 minutes. Zen is authorized only for speech generation. Preserve original video until replacement passes checks.

New-question/held-out evaluation is separate from the exposed-dev comparison. Do not invent human review of new gold or call generated questions held-out. The existing user-reviewed test set may be used only with its actual exposure history stated. Do not silently add unbounded model calls to the 62-request run.
