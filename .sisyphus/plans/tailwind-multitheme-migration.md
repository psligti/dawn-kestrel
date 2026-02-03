# Tailwind v4 Redesign + Session-Scoped Theme Presets

## TL;DR

> **Quick Summary**: Migrate the Vite+React frontend from hand-written CSS to Tailwind v4, redesign the UI, and add session-scoped `themeId` presets that can be changed at runtime (API-persisted + API-pushed). Each theme supports both light and dark; light/dark is a local UI toggle.
>
> **Deliverables**:
> - Tailwind v4 configured for the frontend (`@tailwindcss/vite`)
> - All existing component/global CSS replaced by Tailwind utilities (full migration)
> - Theme presets (by `themeId`) with both light + dark variants
> - Backend stores `theme_id` on sessions and exposes endpoints to update it
> - Backend pushes `theme_id` changes to connected clients (SSE)
> - Frontend theme picker (sets session `themeId` via API) + local light/dark toggle
> - Updated tests (Vitest + pytest) and CI-friendly verification commands
>
> **Estimated Effort**: XL
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Tailwind setup → Theme system → Component migration → Tests

---

## Context

### Original Request
- Use Tailwind for the frontend.
- Full migration (not incremental) and redesign acceptable.
- Support multiple themes, runtime switching.
- `themeId` is set per session, stored in the API, pushed to the UI.
- UI can change session `themeId`.
- Each theme supports light+dark; light/dark is a local UI toggle.

### Codebase Facts (verified)

**Frontend stack**
- Vite + React in `frontend/`
- Tests: Vitest + Testing Library (`frontend/vitest.config.ts`, `frontend/src/__tests__/setup.ts`)

**Existing CSS inventory to replace**
- Global chain: `frontend/src/main.tsx` → `frontend/src/index.css` → `frontend/src/styles/themes.css`
- App CSS: `frontend/src/App.tsx` imports `frontend/src/App.css`
- Component CSS imports (1:1): `frontend/src/components/*.tsx` import matching `*.css`

**Existing theming wiring to refactor**
- Current ThemeProvider: `frontend/src/components/ThemeProvider.tsx` (writes `data-theme` to `document.documentElement`)
- Theme toggle UI: `frontend/src/components/RightDrawer.tsx`
- Theme state in store: `frontend/src/store/index.ts`
- Theme tests: `frontend/src/__tests__/ThemeProvider.test.tsx`

**Existing real-time pattern**
- Frontend SSE/EventSource pattern: `frontend/src/hooks/useExecuteAgent.ts`
- Backend SSE exists only for task streaming: `backend/api/streaming.py` (`GET /api/v1/tasks/{task_id}/stream`)

**Session model & storage (where `theme_id` belongs)**
- Session model: `opencode_python/src/opencode_python/core/models.py`
- Session storage: `opencode_python/src/opencode_python/storage/store.py`
- Session manager: `opencode_python/src/opencode_python/core/session.py`
- Session API endpoints: `backend/api/sessions.py` (no PUT/PATCH today)
- Frontend session types: `frontend/src/types/api.ts`, `frontend/src/store/index.ts`
- Frontend sessions hook: `frontend/src/hooks/useSessions.ts`

### Metis Review (key gaps addressed)
- Runtime themes cannot rely on build-time Tailwind theme alone; use CSS variables keyed by `themeId` and keep Tailwind classes static.
- Add explicit fallback behavior for unknown `themeId`.
- SSE disconnect/reconnect should refetch current session theme.
- Avoid scope creep (do not build a full theme-builder; store only `themeId`, not a full theme object).

---

## Work Objectives

### Core Objective
Replace the frontend styling system with Tailwind v4 and implement a session-scoped `themeId` preset system that can be updated via UI and synchronized via API push.

### Concrete Deliverables
- Tailwind v4 installed and wired into Vite build.
- Frontend uses Tailwind utilities for all layout/styling (remove legacy CSS files/imports).
- Theme presets live in the frontend and are applied by setting the session `themeId` on the API.
- API persists `theme_id` per session and broadcasts changes to clients.

### Definition of Done
- `cd frontend && npm run build` exits 0.
- `cd frontend && npm test` exits 0.
- `cd frontend && npm run lint` exits 0.
- `cd backend && pytest` exits 0.
- Session theme flow works end-to-end via automated checks:
  - Update `theme_id` via API endpoint → SSE pushes event → frontend applies new theme without reload.

### Must Have
- `themeId` presets are runtime-switchable.
- `themeId` is persisted per session (backend).
- UI has a theme picker that updates the session `themeId`.
- Light/dark toggle is purely local UI state.
- No dynamic Tailwind class name generation.

### Defaults Applied (override if needed)
- Theme presets to ship initially: `aurora`, `ocean`, `ember`.
- Default session theme: `aurora`.

### Must NOT Have (Guardrails)
- No “theme builder” UI or arbitrary token editing.
- No storing entire theme token maps in the API; only `theme_id` per session.
- No manual QA steps in acceptance criteria (agent-executable only).
- No broad redesign of component logic/behavior; redesign is styling/layout only.

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES
- **User wants tests**: YES (tests-after)
- **Frameworks**: Vitest (frontend), pytest (backend)

### Verification Commands

Frontend:
- `cd frontend && npm test`
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Backend:
- `cd backend && pytest`

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
- Backend: add `theme_id` to session model + API update endpoint + SSE theme stream
- Frontend: install/configure Tailwind v4 + establish new theme preset token file

Wave 2 (After Wave 1):
- Frontend: theme runtime plumbing (apply `themeId` + `.dark`, session sync, SSE client)
- Frontend: implement theme picker UI in `RightDrawer` and integrate with session update API

Wave 3 (After Wave 2):
- Full component migration CSS→Tailwind + redesign
- Tests updates/expansion + regression coverage

Critical Path: Wave 1 → Wave 2 → Wave 3

---

## TODOs

> Notes:
> - Implementation + tests are combined per task (tests-after still means tests are part of the task’s acceptance criteria).
> - All verification steps are agent-executable.

- [x] 0. Baseline discovery + safety snapshot

  **What to do**:
  - Enumerate current CSS imports and component count.
  - Capture a quick “before” baseline (test/build/lint pass).

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `git-master`

  **References**:
  - `frontend/src/main.tsx` - global CSS entry import
  - `frontend/src/index.css` - imports theme tokens
  - `frontend/src/styles/themes.css` - current theme token set
  - `frontend/src/components/MessageCard.css` - most complex CSS to migrate

  **Acceptance Criteria**:
  - `cd frontend && npm test` exits 0 (baseline)
  - `cd frontend && npm run build` exits 0 (baseline)
  - `cd frontend && npm run lint` exits 0 (baseline)
  - `cd backend && pytest` exits 0 (baseline)

 - [x] 1. Backend: add session `theme_id` to the Session model and persistence

   **What to do**:
   - Extend the Session model to include `theme_id`.
   - Ensure session serialization/deserialization persists it.
   - Ensure new sessions get a default `theme_id` if none is provided.

   **Recommended Agent Profile**:
   - **Category**: `unspecified-low`
   - **Skills**: `git-master`

   **References**:
   - `opencode_python/src/opencode_python/core/models.py` - `Session` model
   - `opencode_python/src/opencode_python/storage/store.py` - session JSON persistence
   - `opencode_python/src/opencode_python/core/session.py` - session create/update

   **Acceptance Criteria**:
   - `cd backend && pytest` exits 0
   - A new/updated backend test demonstrates: create session → `theme_id` saved → read session returns same `theme_id`

 - [x] 2. Backend: add API to update session `theme_id`

   **What to do**:
   - Add a request model (Pydantic) for updating session metadata including `theme_id`.
   - Add `PUT` or `PATCH` endpoint in `backend/api/sessions.py`.
   - Return the updated session including `theme_id`.

   **Must NOT do**:
   - Do not add light/dark mode fields to the API (local UI only).

   **Recommended Agent Profile**:
   - **Category**: `unspecified-low`
   - **Skills**: `git-master`

   **References**:
   - `backend/api/sessions.py` - session endpoints (needs new update route)
   - `backend/tests/api/test_sessions.py` - existing session API tests
   - `opencode_python/src/opencode_python/core/session.py` - update mechanism

   **Acceptance Criteria**:
   - `cd backend && pytest` exits 0
   - A backend API test asserts:
     - Updating `theme_id` returns 200
     - Reading session returns updated `theme_id`

 - [x] 3. Backend: push session theme changes to clients (SSE)

   **What to do**:
   - Implement an SSE endpoint for per-session events (recommended: `GET /api/v1/sessions/{session_id}/stream`).
   - Add an in-memory pub/sub so that when `theme_id` changes, all subscribers for that session receive an event.
   - On connect, emit an initial event with the current `theme_id`.
   - Define event payload shape (e.g., `{ type: "session_theme", session_id, theme_id }`).

   **Recommended Agent Profile**:
   - **Category**: `unspecified-high`
   - **Skills**: `git-master`

   **References**:
   - `backend/api/streaming.py` - existing SSE formatting/pattern
   - `backend/main.py` - FastAPI wiring
   - `backend/api/sessions.py` - where to publish theme updates after write

   **Acceptance Criteria**:
   - `cd backend && pytest` exits 0
   - A backend test can connect to the SSE endpoint and observe a `theme_id` update event after calling the update API.

- [x] 4. Frontend: install + configure Tailwind v4 for Vite

  **What to do**:
  - Add Tailwind v4 dependencies and configure Vite via `@tailwindcss/vite`.
  - Replace the global CSS entry to use Tailwind v4 import (`@import "tailwindcss";`).
  - Ensure dark mode uses class strategy compatible with `.dark`.

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `frontend-ui-ux`

  **References**:
  - `frontend/vite.config.ts` - add Tailwind Vite plugin
  - `frontend/src/main.tsx` - CSS entry import
  - `frontend/src/index.css` - current global reset + theme import

  **Acceptance Criteria**:
  - `cd frontend && npm run build` exits 0
  - `cd frontend && npm run lint` exits 0

- [x] 5. Frontend: implement theme presets (`themeId`) + token mapping

  **What to do**:
  - Define a fixed set of `themeId` presets in the frontend (ship at least: `aurora`, `ocean`, `ember`; each includes light + dark values).
  - Use CSS variables as the token layer selected by `themeId` (e.g., `data-theme="<id>"` on `document.documentElement`).
  - Keep `.dark` for mode; each theme preset provides both modes.
  - Map CSS variables into Tailwind v4 tokens using `@theme inline` so Tailwind utilities remain static.
  - Add an explicit fallback if an unknown `themeId` is received.

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `frontend-ui-ux`

  **References**:
  - `frontend/src/styles/themes.css` - prior token approach to replace
  - `frontend/src/index.css` - where global styles currently live

  **Acceptance Criteria**:
  - `cd frontend && npm run build` exits 0
  - A new/updated frontend test asserts:
    - Applying `themeId` sets the expected root attribute/class
    - Toggling `.dark` changes computed CSS variable values for at least one token

 - [x] 6. Frontend: refactor ThemeProvider to `.dark` + `themeId` (session-scoped)

   **What to do**:
   - Change ThemeProvider so it:
     - Applies `.dark` class for mode only
     - Applies `data-theme` (or an equivalent) for `themeId`
   - Ensure mode persists locally (localStorage ok).
   - Ensure `themeId` comes from current session state, not local-only.

   **Recommended Agent Profile**:
   - **Category**: `unspecified-high`
   - **Skills**: `frontend-ui-ux`

   **References**:
   - `frontend/src/components/ThemeProvider.tsx` - existing theming behavior
   - `frontend/src/__tests__/ThemeProvider.test.tsx` - update assertions
   - `frontend/src/store/index.ts` - theme state hooks/actions

   **Acceptance Criteria**:
   - `cd frontend && npm test` exits 0
   - ThemeProvider tests assert `.dark` toggling and `themeId` application behavior

 - [x] 7. Frontend: extend session types + APIs to include `theme_id`

   **What to do**:
   - Add `theme_id?: string` to session types.
   - Ensure session list/get/create normalize/include `theme_id`.
   - Add a session update method (PUT/PATCH) for `theme_id`.

   **Recommended Agent Profile**:
   - **Category**: `unspecified-low`
   - **Skills**: `frontend-ui-ux`

   **References**:
   - `frontend/src/types/api.ts` - Session interface
   - `frontend/src/store/index.ts` - store Session interface
   - `frontend/src/hooks/useSessions.ts` - session API + normalization
   - `frontend/src/hooks/useApiClient.ts` - has `putApi` helper

   **Acceptance Criteria**:
   - `cd frontend && npm test` exits 0
   - A frontend test asserts normalizeSession preserves `theme_id`

 - [x] 8. Frontend: implement session theme push (SSE client)

   **What to do**:
   - Implement an EventSource hook patterned after `useExecuteAgent.ts` that subscribes to the active session's theme stream.
   - On reconnect, refetch current session to avoid stale theme.
   - Update store so incoming events update current session `theme_id` and apply immediately.

   **Recommended Agent Profile**:
   - **Category**: `unspecified-high`
   - **Skills**: `frontend-ui-ux`

   **References**:
   - `frontend/src/hooks/useExecuteAgent.ts` - SSE connection and backoff
   - `frontend/src/store/index.ts` - session state + actions
   - Backend SSE endpoint implemented in Task 3

   **Acceptance Criteria**:
   - `cd frontend && npm test` exits 0
   - A frontend test mocks EventSource and asserts theme changes are applied

 - [x] 9. Frontend: add a theme picker UI (persist to API)

   **What to do**:
   - Add a theme picker in the existing Settings UI.
   - When user selects a new theme:
     - Optimistically apply it locally
     - Persist via session update API (`theme_id`)
   - Keep light/dark toggle as local only.

   **Recommended Agent Profile**:
   - **Category**: `visual-engineering`
   - **Skills**: `frontend-ui-ux`

   **References**:
   - `frontend/src/components/RightDrawer.tsx` - settings UI location
   - `frontend/src/store/index.ts` - theme + session state
   - `frontend/src/hooks/useSessions.ts` - session update method

   **Acceptance Criteria**:
   - `cd frontend && npm test` exits 0
   - A frontend test asserts selecting a theme triggers an API call and updates the UI state

- [ ] 10. Full CSS → Tailwind migration + redesign (all components)

  **What to do**:
  - Remove CSS imports and migrate each component’s layout/styling to Tailwind utilities.
  - Redesign allowed: update spacing/typography/visual hierarchy, but do not change business logic.
  - Special handling:
    - Scrollbars (if needed) via custom utilities or minimal CSS layers
    - Animations via Tailwind utilities / keyframes in global CSS layer

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: `frontend-ui-ux`

  **References**:
  - CSS import list (to remove):
    - `frontend/src/App.tsx`, `frontend/src/App.css`
    - `frontend/src/components/AppLayout.tsx`, `frontend/src/components/AppLayout.css`
    - `frontend/src/components/MessageCard.tsx`, `frontend/src/components/MessageCard.css`
    - `frontend/src/components/RightDrawer.tsx`, `frontend/src/components/RightDrawer.css`
    - `frontend/src/components/TopBar.tsx`, `frontend/src/components/TopBar.css`
    - `frontend/src/components/CommandPalette.tsx`, `frontend/src/components/CommandPalette.css`
    - `frontend/src/components/ComposerBar.tsx`, `frontend/src/components/ComposerBar.css`
    - `frontend/src/components/Navigator.tsx`, `frontend/src/components/Navigator.css`
    - `frontend/src/components/SessionsList.tsx`, `frontend/src/components/SessionsList.css`
    - `frontend/src/components/StatusBar.tsx`, `frontend/src/components/StatusBar.css`

  **Acceptance Criteria**:
  - No component `.css` imports remain in `frontend/src/`.
  - `cd frontend && npm test` exits 0
  - `cd frontend && npm run lint` exits 0
  - `cd frontend && npm run build` exits 0

- [ ] 11. Update/expand tests for theme + session flows (tests-after)

  **What to do**:
  - Add/adjust tests so the new session theme flow is covered:
    - Session fetch applies `theme_id`
    - Theme picker updates session via API
    - SSE event updates session theme in store
    - `.dark` toggle works independent of session theme

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: `frontend-ui-ux`

  **References**:
  - `frontend/src/__tests__/ThemeProvider.test.tsx`
  - `frontend/src/components/RightDrawer.test.tsx`
  - `frontend/src/hooks/useSessions.ts`
  - `frontend/src/hooks/useExecuteAgent.ts`

  **Acceptance Criteria**:
  - `cd frontend && npm test` exits 0

---

## Commit Strategy (suggested)

If you want atomic commits:
- Commit 1: backend `theme_id` + update endpoint + SSE
- Commit 2: Tailwind v4 wiring + new theme preset token layer
- Commit 3+: component migration batches (by complexity)
- Final commit: tests cleanup + lint/build

---

## Success Criteria

- Tailwind v4 is the only styling system used for layout/components (legacy component CSS removed).
- Session `theme_id` can be changed via UI and persisted via API.
- Session `theme_id` updates are pushed via SSE and applied immediately.
- Light/dark toggle remains local UI-only.
- All automated checks pass:
  - Frontend: `npm test`, `npm run lint`, `npm run build`
  - Backend: `pytest`
