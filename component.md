# NCD Evidence — component specification

Status: APPROVED — single-column Claude-inspired composer with Perplexity-style citation navigation. A–D proposals are rejected.
Read design.md and this file before every frontend edit. Use Hallmark and ui-ux-pro-max.

## Shared components
| Component | Behavior | Required states |
|---|---|---|
| QuestionComposer | Controlled textarea, explicit submit, preserve text on failure | empty, filled, focus, submitting, disabled, error, completed |
| RetrievalControls | Reranker ON/OFF affects request; local answer cache OFF displayed | selected, focus, hover, active, disabled during request |
| AnswerPanel | Backend answer rendered faithfully; clear abstention and failure | initial, loading, answered, insufficient evidence, error |
| CitationLink | Navigate to matching source and highlight actual matched quote | default, hover, focus, active, unavailable source |
| EvidenceReader | Document, edition, PDF page, section, query, exact retrieved text | empty, selected, cited, uncited, truncated, failure |
| RunInspector | Actual trace and observed metrics only | empty, pending, completed, failed; never fabricated metrics |

## Approved composition
- AboutSystem: footer disclosure using the existing Sheet primitive; explain the pipeline and recorded evaluation with version/scope caveats. Escape closes and focus returns to the trigger. No API request or fabricated live metric.
- AppShell: minimal wordmark, server status and clear-session action; no persistent sidebar.
- Composer: Thai textarea, settings popover, send button. Ctrl/Cmd+Enter submits; Enter inserts a line. Preserve failed input. Disable during active request. No localStorage or question persistence.
- SettingsPopover: shadcn Popover and Switch for reranker; fixed no-cache explanation. Keep implementation details inside this disclosure.
- ResponseTurn: question, faithful answer, inline citation buttons, sources button, copy and collapsed trace. Status must distinguish answered, abstention and service failure.
- EvidenceSheet: shadcn Sheet with accessible heading, Escape and focus return. List all retrieved sources; highlight whitespace-normalized quote matches without changing source text. Structured table quotes displayed separately when not contiguous. No fake PDF viewer.
- Each turn binds its own answer, source IDs and runtime settings. Source S1 from one turn must never select S1 from another turn.
- UI primitives: generated shadcn Button, Textarea, Popover, Switch, Sheet. Font/icon/token usage shared across components.

## Rejected alternatives (archive)
- A: QuestionComposer + AnswerPanel beside EvidenceReader.
- B: QuestionComposer above source results and selected EvidenceReader.
- C: proposed RunHistory + RetrievalControls + AnswerPanel + EvidenceReader + RunInspector.
- D: proposed DocumentReader + PassageSelection + contextual QuestionComposer.

## State and accessibility contract
- Full interactive visual coverage: default, hover, focus-visible, active, disabled, loading, error, success. Do not invent validation success for a purely local setting.
- Use shadcn/ui primitives with proper native semantics in production; no custom div masquerading as input/button.
- Visible labels; announce selected, loading and error states; preserve focus and user input.
- Color is supplementary: use text/status labels to distinguish retrieved and cited evidence.
- Production React uses the existing /api/ask and /api/health routes. Browser verification fixtures are explicitly separate from a fresh live model request.
- No localStorage persistence, PDF upload, PDF rendering or backend conversation memory is included in this redesign.
