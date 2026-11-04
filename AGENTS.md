# Frontend design contract

Before every frontend or UI change:
1. Read root design.md and component.md.
2. Apply both Hallmark and ui-ux-pro-max skills.
3. Respect their approval status. Draft explorations are not permission to replace the production interface.
4. Keep controls, labels, states, spacing and tokens consistent with the approved design. If a requested change conflicts, surface the conflict before implementation.
5. Verify responsive layouts and keyboard behavior for the changed scope; distinguish fixture demos from live backend verification.

Do not delete or replace the existing website as part of a design exploration. The agreed future frontend stack is React, TypeScript, Vite, Tailwind and shadcn/ui, using the existing FastAPI backend.
