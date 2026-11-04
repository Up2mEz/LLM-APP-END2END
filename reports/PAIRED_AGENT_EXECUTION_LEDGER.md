# Paired old/current execution ledger

- User clarified ReAct agent loop, not React frontend, and requested a fair old/new evaluation. Prior explanation confused these terms; glossary corrected.
- Recovered all 18 v30 locked files. Config recovered by changing the historical max_sources default from 12 to 20 and normalizing LF; SHA-256 exactly matches the archived v30 lock. Historical predictions are not loaded.
- Comparison controls deliberately normalize transport, settings, cache policy and the cache-aware reranker; old Agent/retriever/helper code remains historical. The comparison is therefore old/current agent logic under common execution controls, not a replay of historical service conditions.
- Both arms hybrid/reranker ON, answer/reranker cache OFF, 60 exposed dev questions, 120 fresh requests, alternating order. Same proxy/model, temperature 0,6 rounds,3 searches,150 seconds per request. Luna xhigh blinded judgment planned for both arms.
- Independent review 1 found resumed wall-time accounting and non-durable reservations; both corrected. Review 2 found that blocking retrieval could exceed cooperative timeout; parent process now bounds each worker request and terminates a stalled worker. Timeouts remain errors, conservative 12-attempt accounting, no replacement results.
- Windows real-write check found fsync requires the reopened final file to be writable; changed rb to r+b before any model request. Added real filesystem regression alongside mocked interruption/deadline tests. Five focused tests passed.
- Initial pre-inference startup attempt failed on fsync without dispatching any question. Same run preserves its absolute four-hour deadline; manifest harness hash was finalized before any answer records existed.
- Current production runtime and capstone-current-v2 outputs remain unchanged. No claim of improvement until both arms and judgments finish.
- Independent review 3 reported no remaining material issues after worker timeout enforcement. Reviewer inspected tests without executing them. Root executed five focused tests successfully; real paired inference is running. Review IDs: paired-agent-review-20261105-1, -2, -3 (T3-owned child tasks).
