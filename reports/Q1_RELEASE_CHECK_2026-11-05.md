# Repository release verification

Checked application commit: `0615c4b` (runtime unchanged from the current evaluation).

- Created a separate Git clone under ignored `private/q1-clean-check` and a new Python 3.12.13 virtual environment, without copying the existing environment or credentials.
- Installed `requirements-runtime.txt`; installation log reports all packages installed. PowerShell returned 1 around redirected pip warning/notice output, so dependency consistency and execution were checked separately: `pip check` passed, 209 tests passed with one Starlette deprecation warning.
- Downloaded all 34 data files through `scripts/public_data.py fetch` from the public release. Current evaluation manifest/code/data/questions verification passed in the clone.
- `npm ci` completed with zero reported vulnerabilities and production frontend build passed. Built assets matched the committed files.
- Real retrieval doctor completed with data present and five returned evidence entries. This check reused the machine's existing model-weight cache; a fresh weight download was not tested. No class-proxy credentials were copied, so `proxy_configured=false` is expected. No new Gemma call or new answer-quality score is claimed in this release check.
- The prior current evaluation remains the evidence for real class-proxy calls. Its raw outputs remain local; a fresh reproduction requires credentials and new model calls, followed by judging as documented.
- Bounded scan of 333 tracked files found no high-confidence API-token/private-key patterns; only `.env.example` is tracked. This is not an exhaustive security audit.
- Repository visibility verified public. README now leads with the current evaluation and explains historical scores, source IDs and frontend/backend roles.

The Python launcher on this machine did not recognize `py -3.12`; the new environment was created from its installed Python 3.12 interpreter. README includes the uv alternative. No production runtime or frozen evaluation hashes were changed for this release.
