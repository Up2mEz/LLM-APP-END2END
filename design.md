# NCD Evidence — design direction

Status: APPROVED direction — user accepted Claude-style simplicity with Perplexity-style citations and authorized implementation. The A–D explorations were rejected.

## Approved composition (takes precedence over exploratory notes below)
- Project explanation is an on-demand footer sheet, authorized with the demo/report update. Preserve the single conversation column and existing tokens.
- Single conversation column. Initial screen: restrained wordmark, short Thai heading, large composer, optional example questions. No mascot, dashboard, marketing hero, permanent multi-pane layout or fake metrics.
- Responses form independent question/answer turns in memory only. Clearly state that each question is independent; backend currently does not consume conversation history.
- Citations are inline buttons plus a compact sources entry. Open a source sheet on demand; desktop right side, mobile full width. All retrieved sources remain available even when the agent abstains.
- Settings are a small popover inside the composer. Reranker on by default; disabled while request runs. Local LLM/reranker score cache always off for web questions.
- Advanced trace collapsed beneath response. No permanently visible latency dashboard.
- Theme: light warm-neutral paper, graphite ink, restrained teal citations. Inspired by product interaction patterns, not pixel copying. Self-host Inter Variable and Noto Sans Thai Variable; no external font requests.
- Tokens live in frontend/src/tokens.css; old root tokens.css remains only for legacy static UI. Radius 8/16/24, semantic 4 px spacing, readable 16 px Thai body. Native focus and keyboard semantics from shadcn/Radix.
- Implementation: frontend/ React/TypeScript/Vite/Tailwind/shadcn; build under static/app/. FastAPI serves new root when built, preserving legacy files.

## Confirmed
- Audience: people testing Thai NCD document question answering.
- Tone: modern technical research tool; light, spacious, readable. No mascot or oversized marketing hero in the new workspace.
- Stack: React + TypeScript + Vite + Tailwind + shadcn/ui; existing FastAPI backend.
- Use Hallmark and ui-ux-pro-max for frontend design work. Read this file AND component.md before every frontend modification.
- Preserve current backend behavior, evidence provenance, no-cache request behavior and reranker control unless separately authorized.

## Rejected exploration archive (not implementation requirements)
Interactive exploration: output/design-exploration/index.html.
- A Research Reader: answer and source side by side; citation navigation is primary.
- B Search Studio: query first, results list with source inspector.
- C Experiment Workbench: run history, configuration, response, evidence, trace.
- D Document Workspace: document first, selected passage as question context.
Run history, PDF viewer, passage selection and new endpoint behavior are proposals, not existing implemented capabilities.

## Earlier exploration notes (superseded by approved composition)
- Light neutral surfaces, cobalt accent, dark readable ink, restrained 6–8 px rounding.
- Hairline separators and workspace structure instead of repeated floating cards.
- Thai-readable sans typography; demo uses installed system fonts. Final font selection remains reviewable.
- Color, typography, spacing and state values must use named tokens. Current demo tokens are scoped to the standalone prototype and do not replace production tokens.css.
- Native keyboard semantics, visible focus, minimum 44 px controls, no hover-only actions.
- Check 320, 375, 414, 768 and desktop. Collapse panes in a meaningful reading order.
- No invented latency, accuracy, document counts or medical claims. Clearly label fixture/demo content.

## Implementation authorization
User approved the recommendation and asked to begin redesign. Implement the approved single-column flow. Do not delete old files; validate API integration, errors, source matching, keyboard, responsive layouts and a live request before handoff.
