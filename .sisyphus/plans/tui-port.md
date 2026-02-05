# TUI Port: TypeScript OpenCode to Python/Textual

## TL;DR

> **Quick Summary**: Port TypeScript OpenCode TUI (~13,000 lines, 50 files) to Python/Textual with 100% feature parity. This is a **multi-phase project** - Phase 1 focuses on core workflows (session management, messaging, basic navigation, 3 essential dialogs, 3 essential themes).
>
> **Deliverables**:
> - Enhanced OpenCodeTUI app with session management, message timeline, dialog system
> - Session list and selection dialogs
> - Model/theme selection dialogs
> - Message rendering with all part types
> - Basic prompt input with streaming support
> - Essential keyboard bindings and navigation
>
> **Estimated Effort**: Large (2-3 weeks for Phase 1)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: TUI testing infra → Keybinding system → Dialog infrastructure → MessageScreen enhancement

---

## Context

### Original Request
"Create the full fidelity tui from ./opencode in opencode_python/src/opencode_python"

### Interview Summary
**Key Discussions**:
- **Scope**: 100% feature parity from TypeScript TUI to Python/Textual
- **Architecture**: Adapt to Textual idioms (NOT 1:1 replication of provider pattern)
- **Testing**: TDD with pytest-asyncio (test infrastructure exists)

**Research Findings**:
- **TypeScript TUI**: 50 files, ~13,114 lines, SolidJS + @opentui framework
  - 18 dialog components
  - 12 context providers (sync, local, theme, sdk, route, keybind, kv, etc.)
  - 10 UI primitives (dialog-select, dialog-prompt, toast, spinner, etc.)
  - 2 main routes (home.tsx, session/index.tsx with 9 subfiles)
  - 5 utility modules (clipboard, editor, transcript, terminal, signal)
- **Python TUI**: 6 files, ~2,046 lines, Textual framework
  - Already: app.py (261 lines), message_view.py (264 lines), message_screen.py (550 lines)
  - Already: context_browser.py (510 lines), diff_viewer.py (458 lines)
  - **Coverage**: ~10% of TypeScript features
- **Textual Framework**: Built-in widgets (DataTable, Input, Tabs, ScrollableContainer, etc.), CSS styling, screen stack management, reactive system, no provider pattern needed
- **Key Architecture Differences**:
  - TS: SolidJS reactive stores + provider/context pattern
  - Python: Textual reactive attributes + screen stack + app-level state

### Metis Review
**Critical Discovery**: This is NOT a mid-sized task. It's a **large-scale multi-phase port** requiring:
- Phased delivery (cannot do 13,114 lines in one PR)
- Explicit Phase 1 scope with "Must NOT Have" section
- Guardrails against scope creep (themes, dialogs, prompt system)
- TUI testing strategy establishment BEFORE writing tests

**Guardrails Applied** (from Metis review):
- MUST NOT implement custom dialog system - use Textual's `ModalScreen`
- MUST NOT implement provider/context pattern - use Textual reactive system
- MUST NOT port all 30+ themes - limit to 3-5 essential themes
- MUST NOT port full prompt system (history, autocomplete, stash) - start with input+submit only
- MUST NOT port all 18 dialogs - limit to 3-5 essential dialogs
- MUST NOT implement complex state management - use Textual's `reactive` decorator and `Var`
- MUST NOT assume 1:1 code mapping - estimate separately for each component

---

## Work Objectives

### Core Objective
Port TypeScript OpenCode TUI core features to Python/Textual, establishing a functional TUI with session management, message timeline, and essential dialogs while adapting to Textual idioms.

### Concrete Deliverables
- Enhanced `OpenCodeTUI` app in `opencode_python/src/opencode_python/tui/app.py`
- Dialog system in `opencode_python/src/opencode_python/tui/dialogs/` directory
- Keybinding system in `opencode_python/src/opencode_python/tui/keybindings.py`
- Enhanced screens in `opencode_python/src/opencode_python/tui/screens/`
- TUI testing infrastructure in `tests/tui/`
- Theme definitions in `opencode_python/src/opencode_python/tui/themes/`

### Definition of Done
- [ ] User can launch TUI (`opencode tui`)
- [ ] Session list displays with navigation
- [ ] User can select and open session
- [ ] Message timeline renders messages correctly
- [ ] User can submit prompts and see responses
- [ ] Essential dialogs work (session-list, model-select, theme-select)
- [ ] Keyboard navigation works (arrows, q, Ctrl+C, / for commands)
- [ ] 3 themes switch correctly
- [ ] All tests pass (pytest tests/tui/)
- [ ] Manual QA checklist verified

### Must Have (Phase 1)
- Session list view with DataTable and selection
- Session detail view with message timeline
- Message rendering (user, assistant, system roles)
- Text part display with Markdown widget
- Tool part display (bash, read, grep, glob, write, edit)
- Basic input prompt (text only, no autocomplete)
- Essential keyboard shortcuts (q, Ctrl+C, arrow keys, slash commands)
- 3 essential dialogs (session-list, model-select, theme-select)
- 3 essential themes (light, dark, dracula)
- Dialog infrastructure using Textual's ModalScreen
- Keybinding system using Textual's BINDINGS and Actions
- TDD workflow with pytest-asyncio

### Must NOT Have (Guardrails)
- [ ] File part rendering with preview
- [ ] Autocomplete for input
- [ ] Command history (up/down arrows)
- [ ] Prompt stash
- [ ] Frecency tracking
- [ ] 27 other themes (beyond light, dark, dracula)
- [ ] 15 other dialogs (beyond 3 essentials)
- [ ] Complex keyboard shortcuts (beyond 6 essentials)
- [ ] Accessibility features (screen reader support)
- [ ] Custom dialog system (use Textual's ModalScreen)
- [ ] Provider pattern state management (use Textual reactive)
- [ ] Custom syntax highlighter (use Textual's Markdown widget)
- [ ] Virtual text with extmarks (use Textual's standard widgets)

---

## Verification Strategy (MANDATORY)

> **CRITICAL: TDD APPROACH - Write tests BEFORE implementation**

### Test Decision
- **Infrastructure exists**: YES (pytest, pytest-asyncio)
- **User wants tests**: TDD (Test-Driven Development)
- **Framework**: pytest-asyncio for async testing
- **QA approach**: Automated widget tests + manual QA checklist

### If TDD Enabled

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: `tests/tui/test_<component>.py`
   - Test command: `pytest tests/tui/test_<component>.py`
   - Expected: FAIL (test exists, implementation doesn't)

2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/tui/test_<component>.py`
   - Expected: PASS

3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/tui/test_<component>.py`
   - Expected: PASS (still)

**Test Setup Task** (if infrastructure doesn't exist):
- [ ] 0. Setup TUI Testing Infrastructure
  - Install: pytest-asyncio already in dependencies
  - Config: Create `tests/conftest.py` with Textual app fixtures
  - Verify: `pytest tests/tui/test_app.py` → imports succeed
  - Example: Create `tests/tui/test_app.py` with basic app test
  - Verify: `pytest tests/tui/` → 1 test passes

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.

```
Wave 1 (Start Immediately):
├── Task 0: Setup TUI Testing Infrastructure
└── Task 1: Create Keybinding System

Wave 2 (After Wave 1):
├── Task 2: Create Dialog Infrastructure
├── Task 3: Create Session List Screen
└── Task 4: Create Model Select Dialog

Wave 3 (After Wave 2):
├── Task 5: Create Theme Select Dialog
├── Task 6: Enhance MessageScreen (scroll navigation)
└── Task 7: Implement Command Palette

Wave 4 (After Wave 3):
├── Task 8: Enhance Header (breadcrumbs, model display)
├── Task 9: Enhance Footer (keyboard hints, status)
└── [x] 10. Define 3 Essential Themes
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|-------------------|
| 0 | None | 1, 2, 3, 4 | None (must start first) |
| 1 | 0 | 5, 7 | 2, 3, 4 |
| 2 | 0, 1 | 5, 6, 7, 8 | 3, 4 |
| 3 | 0, 1, 2 | 6 | 4, 5 |
| 4 | 0, 1 | 5 | 2, 3 |
| 5 | 1, 2 | 6, 8, 10 | 3, 4, 6, 7 |
| 6 | 2, 3 | 8 | 5, 7 |
| 7 | 1 | 8, 9 | 5, 6 |
| 8 | 2, 5 | 10 | 6, 7, 9 |
| 9 | 7 | 10 | 8 |
| 10 | None | None | 8, 9 |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 0, 1 | delegate_task(category="unspecified-low", load_skills=["git-master"], run_in_background=true) |
| 2 | 2, 3, 4 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) |
| 3 | 5, 6, 7 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) |
| 4 | 8, 9, 10 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) |

---

## TODOs

> **IMPLEMENTATION + TEST = ONE Task. Never separate.**
> **EVERY task MUST have: Recommended Agent Profile + Parallelization info.**

---

### Wave 1: Foundation

- [x] 0. Setup TUI Testing Infrastructure

  **What to do**:
  - [x] Create `tests/tui/` directory
  - [x] Create `tests/conftest.py` with Textual app fixtures
  - [x] Create `tests/tui/test_app.py` with basic app test
  - [x] Create test utilities for widget testing

  **Must NOT do**:
  - [ ] Do NOT create complex headless testing setup
  - [ ] Do NOT use screenshot testing initially

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Test infrastructure setup is straightforward task
  - **Skills**: `[]`
    - No special skills needed for test setup

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (must complete first)
  - **Blocks**: Tasks 1-10 (all depend on testing infrastructure)
  - **Blocked By**: None (foundational task)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `tests/conftest.py` - Existing pytest fixtures (if any)
  - `tests/` - Existing test structure patterns
  - `pytest-asyncio` docs - https://pytest-asyncio.readthedocs.io/

  **API/Type References** (contracts to implement against):
  - `textual.app.App` - Textual app class for testing
  - `pytest` - Testing framework
  - `pytest-asyncio` - Async test support

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual testing guide: https://textual.textualize.io/guide/testing/
  - pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for test examples)
  - pytest documentation: https://docs.pytest.org/

  **WHY Each Reference Matters** (explain the relevance):
  - `tests/conftest.py`: Provides test fixtures and setup patterns
  - `pytest-asyncio docs`: Essential for async Textual app testing
  - Textual testing guide: Shows how to test widgets and screens

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_app.py
  - [ ] Test file imports textual.app.App
  - [ ] pytest tests/tui/test_app.py → FAIL (no implementation yet)

  **TDD - GREEN Phase:**
  - [ ] conftest.py created with app fixtures
  - [ ] tests/tui/test_app.py basic test passes
  - [ ] pytest tests/tui/ → 1 test passes

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_app.py -v
  # Assert: Exit code 0
  # Assert: 1 test collected and passed
  ```

  **Evidence to Capture:**
  - [ ] Test output showing PASS
  - [ ] pytest configuration verification

  **Commit**: YES | NO (groups with 1)
  - Message: `test(tui): setup TUI testing infrastructure`
  - Files: `tests/conftest.py`, `tests/tui/test_app.py`
  - Pre-commit: `pytest tests/tui/`

---

- [x] 1. Create Keybinding System

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/keybindings.py`
  - [x] Define essential keybindings (q, Ctrl+C, arrows, /, Enter, Escape)
  - [x] Integrate with Textual's BINDINGS and Actions system
  - [x] Create keybinding context for per-screen bindings
  - [x] Write tests for keybinding registration and execution

  **Must NOT do**:
  - [ ] Do NOT implement complex context-sensitive keybinding system
  - [ ] Do NOT port all 50+ TypeScript shortcuts
  - [ ] Do NOT implement keybinding UI editor

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Keybinding system is straightforward utility task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0)
  - **Blocks**: Tasks 5, 7
  - **Blocked By**: Task 0 (testing infrastructure)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/tui/app.py:62-64` - Existing BINDINGS pattern
  - `../../opencode/packages/opencode/src/cli/cmd/tui/context/keybind.tsx` - TypeScript keybinding context structure
  - `../../opencode/packages/opencode/src/cli/cmd/tui/component/dialog-command.tsx:66-72` - Keybinding registration

  **API/Type References** (contracts to implement against):
  - `textual.binding.Binding` - Textual binding class
  - `textual.app.App.BINDINGS` - App-level bindings attribute

  **Test References** (testing patterns to follow):
  - Textual actions guide: https://textual.textualize.io/guide/actions/

  **Documentation References** (specs and requirements):
  - Textual documentation: https://textual.textualize.io/guide/actions/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for action examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `app.py:62-64`: Shows existing BINDINGS pattern to extend
  - `keybind.tsx`: TypeScript keybinding context for reference structure
  - `dialog-command.tsx`: Shows how keybindings are registered and matched

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_keybindings.py
  - [ ] Test defines essential keybindings (q, Ctrl+C, arrows, /, Enter, Escape)
  - [ ] pytest tests/tui/test_keybindings.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] keybindings.py created with BINDINGS class
  - [ ] Essential keybindings defined and working
  - [ ] pytest tests/tui/test_keybindings.py → PASS (all keybinding tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_keybindings.py -v
  # Assert: Exit code 0
  # Assert: All 6 keybinding tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing all keybindings registered
  - [ ] Test coverage for keybinding execution

  **Commit**: YES | NO (groups with 2, 3, 4)
  - Message: `feat(tui): create keybinding system with essential shortcuts`
  - Files: `opencode_python/src/opencode_python/tui/keybindings.py`, `tests/tui/test_keybindings.py`
  - Pre-commit: `pytest tests/tui/test_keybindings.py`

---

### Wave 2: Core Dialogs and Screens

- [x] 2. Create Dialog Infrastructure

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/dialogs/__init__.py`
  - [x] Create base `BaseDialog` class extending `ModalScreen`
  - [x] Implement standard dialog patterns (ok/cancel, confirm, select, prompt)
  - [x] Create tests for dialog lifecycle (show, close, return value)
  - [x] Write tests for all dialog types

  **Must NOT do**:
  - [ ] Do NOT create complex dialog transition animations
  - [ ] Do NOT implement custom dialog stack (use Textual's screen stack)
  - [ ] Do NOT replicate TypeScript dialog system 1:1

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Dialog infrastructure is reusable utility
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/ui/dialog.tsx` - TypeScript base dialog class
  - `../../opencode/packages/opencode/src/cli/cmd/tui/ui/dialog-select.tsx` - TypeScript dialog select pattern
  - `../../opencode/packages/opencode/src/cli/cmd/tui/ui/dialog-confirm.tsx` - TypeScript confirm dialog pattern

  **API/Type References** (contracts to implement against):
  - `textual.screen.ModalScreen` - Textual modal screen class
  - `textual.widgets.Button` - Button widget for dialog actions
  - `textual.widgets.Label` - Label widget for dialog content

  **Test References** (testing patterns to follow):
  - Textual screen guide: https://textual.textualize.io/guide/screens/#modal-screens

  **Documentation References** (specs and requirements):
  - Textual documentation: https://textual.textualize.io/guide/screens/#modal-screens

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for modal screen examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `ui/dialog.tsx`: Shows dialog lifecycle and structure to adapt
  - `ui/dialog-select.tsx`: Shows how to build selection dialogs with DataTable
  - `ui/dialog-confirm.tsx`: Shows confirm dialog pattern with yes/no buttons

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_dialogs.py
  - [ ] Test for BaseDialog class
  - [ ] Tests for SelectDialog, ConfirmDialog, PromptDialog
  - [ ] pytest tests/tui/test_dialogs.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] dialogs/__init__.py created with BaseDialog
  - [ ] SelectDialog implemented (title, options, on_select)
  - [ ] ConfirmDialog implemented (title, on_confirm)
  - [ ] PromptDialog implemented (title, placeholder, on_submit)
  - [ ] pytest tests/tui/test_dialogs.py → PASS (all dialog tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_dialogs.py -v
  # Assert: Exit code 0
  # Assert: All dialog lifecycle tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing dialog show/close behavior
  - [ ] Screenshots of dialog appearance (optional)

  **Commit**: YES | NO (groups with 3, 4)
  - Message: `feat(tui): create dialog infrastructure with base classes`
  - Files: `opencode_python/src/opencode_python/tui/dialogs/__init__.py`, `tests/tui/test_dialogs.py`
  - Pre-commit: `pytest tests/tui/test_dialogs.py`

---

- [x] 3. Create Session List Screen

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/screens/session_list_screen.py`
  - [x] Use DataTable to display sessions (id, title, time)
  - [x] Implement session selection with Enter key
  - [x] Handle session loading and navigation to MessageScreen
  - [x] Write tests for session list rendering and selection

  **Must NOT do**:
  - [x] Do NOT implement complex session filtering/search yet
  - [x] Do NOT add session deletion/forking dialogs (Phase 2+)
  - [x] Do NOT implement session status indicators yet

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Session list screen is straightforward UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1, 2)
  - **Blocks**: Task 6
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/tui/app.py:84-88` - Existing DataTable usage for sessions
  - `../../opencode/packages/opencode/src/cli/cmd/tui/component/dialog-session-list.tsx` - TypeScript session list dialog
  - `opencode_python/src/opencode_python/tui/screens/message_screen.py` - Existing screen pattern to follow

  **API/Type References** (contracts to implement against):
  - `textual.widgets.DataTable` - Table widget for session display
  - `textual.screen.Screen` - Screen class for session list
  - `opencode_python.core.models.Session` - Session model type

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual DataTable docs: https://textual.textualize.io/widgets/data-table/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for DataTable examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `app.py:84-88`: Shows existing DataTable pattern for sessions
  - `dialog-session-list.tsx`: Shows session list UI pattern to adapt
  - `message_screen.py`: Shows screen structure and navigation patterns

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_session_list_screen.py
  - [ ] Test for session list rendering
  - [ ] Test for session selection and navigation
  - [ ] pytest tests/tui/test_session_list_screen.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] session_list_screen.py created with DataTable
  - [ ] Sessions displayed with columns (id, title, time)
  - [ ] Enter key opens selected session
  - [ ] pytest tests/tui/test_session_list_screen.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_session_list_screen.py -v
  # Assert: Exit code 0
  # Assert: All session list tests pass
  ```

  **Evidence to Capture**:
  - [ ] Test output showing session list rendering
  - [ ] Screenshots of session list (optional)

  **Commit**: YES | NO (groups with 4)
  - Message: `feat(tui): create session list screen with DataTable`
  - Files: `opencode_python/src/opencode_python/tui/screens/session_list_screen.py`, `tests/tui/test_session_list_screen.py`
  - Pre-commit: `pytest tests/tui/test_session_list_screen.py`

---

- [x] 4. Create Model Select Dialog

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/dialogs/model_select_dialog.py`
  - [x] Extend BaseDialog with SelectDialog
  - [x] Display available models (from settings/provider)
  - [x] Handle model selection and persistence
  - [x] Write tests for model selection and persistence

  **Must NOT do**:
  - [x] Do NOT implement fuzzy search yet (Phase 2+)
  - [x] Do NOT add model favorites/recents (Phase 2+)
  - [x] Do NOT implement provider selection yet (Phase 2+)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Model select dialog is straightforward UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1, 2)
  - **Blocks**: Task 5
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/component/dialog-model.tsx` - TypeScript model select dialog
  - `opencode_python/src/opencode_python/core/settings.py` - Settings model management
  - `opencode_python/src/opencode_python/tui/dialogs/__init__.py` - Base dialog class to use

  **API/Type References** (contracts to implement against):
  - `opencode_python.providers.ProviderID` - Provider type
  - `opencode_python.core.settings.get_settings()` - Settings access
  - `textual.widgets.Label` - Label widget for model display

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual select dialog: https://textual.textualize.io/guide/screens/#modal-screens

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for select examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `dialog-model.tsx`: Shows model select UI pattern to adapt
  - `settings.py`: Shows how to access available models
  - `dialogs/__init__.py`: Shows BaseDialog to extend

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_model_select_dialog.py
  - [ ] Test for model list rendering
  - [ ] Test for model selection and persistence
  - [ ] pytest tests/tui/test_model_select_dialog.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] model_select_dialog.py created with model list
  - [ ] Models displayed from settings
  - [ ] Selection persists to settings
  - [ ] pytest tests/tui/test_model_select_dialog.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_model_select_dialog.py -v
  # Assert: Exit code 0
  # Assert: All model select tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing model selection
  - [ ] Verification of settings persistence

  **Commit**: YES | NO (groups with 5, 6)
  - Message: `feat(tui): create model select dialog`
  - Files: `opencode_python/src/opencode_python/tui/dialogs/model_select_dialog.py`, `tests/tui/test_model_select_dialog.py`
  - Pre-commit: `pytest tests/tui/test_model_select_dialog.py`

---

### Wave 3: Enhanced Features

- [x] 5. Create Theme Select Dialog

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/dialogs/theme_select_dialog.py`
  - [x] Extend BaseDialog with SelectDialog
  - [x] Display 3 essential themes (light, dark, dracula)
  - [x] Implement theme switching with CSS application
  - [x] Write tests for theme selection and application

  **Must NOT do**:
  - [x] Do NOT port all 30+ themes from TypeScript
  - [x] Do NOT implement custom theme editor yet
  - [x] Do NOT add theme preview screenshots yet

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Theme select dialog is straightforward UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1, 2)
  - **Blocks**: Tasks 6, 8, 10
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/component/dialog-theme-list.tsx` - TypeScript theme list dialog
  - `../../opencode/packages/opencode/src/cli/cmd/tui/context/theme.tsx` - TypeScript theme system
  - `opencode_python/src/opencode_python/tui/dialogs/__init__.py` - Base dialog class to use

  **API/Type References** (contracts to implement against):
  - `textual.app.App.theme` - App theme attribute
  - `textual.app.App.CSS` - App CSS attribute
  - `textual.widgets.Label` - Label widget for theme display

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual CSS guide: https://textual.textualize.io/guide/css/
  - Textual theming: https://textual.textualize.io/guide/styling/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for theme examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `dialog-theme-list.tsx`: Shows theme list UI pattern to adapt
  - `context/theme.tsx`: Shows theme system structure (simplified to 3 themes)
  - `dialogs/__init__.py`: Shows BaseDialog to extend

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_theme_select_dialog.py
  - [ ] Test for theme list rendering (3 themes)
  - [ ] Test for theme switching and CSS application
  - [ ] pytest tests/tui/test_theme_select_dialog.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] theme_select_dialog.py created with 3 themes
  - [ ] Themes displayed (light, dark, dracula)
  - [ ] Theme switching applies CSS correctly
  - [ ] pytest tests/tui/test_theme_select_dialog.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_theme_select_dialog.py -v
  # Assert: Exit code 0
  # Assert: All theme select tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing theme selection
  - [ ] Screenshots of each theme (optional)

  **Commit**: YES | NO (groups with 6, 8, 10)
  - Message: `feat(tui): create theme select dialog with 3 essential themes`
  - Files: `opencode_python/src/opencode_python/tui/dialogs/theme_select_dialog.py`, `tests/tui/test_theme_select_dialog.py`
  - Pre-commit: `pytest tests/tui/test_theme_select_dialog.py`

---

- [x] 6. Enhance MessageScreen (scroll navigation)

  **What to do**:
  - [x] Enhance `opencode_python/src/opencode_python/tui/screens/message_screen.py`
  - [x] Add scroll navigation (page up/down, half page, line-by-line)
  - [x] Add jump to first/last message (G, Shift+G)
  - [x] Add line numbers for tool output (optional)
  - [x] Write tests for scroll navigation commands

  **Must NOT do**:
  - [x] Do NOT implement virtual scrolling (use Textual's ScrollableContainer)
  - [x] Do NOT add animations yet (Phase 2+)
  - [x] Do NOT implement message search/filtering yet (Phase 2+)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Message screen enhancement is straightforward UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1, 2, 3)
  - **Blocks**: Tasks 7, 8, 9
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/tui/screens/message_screen.py` - Existing MessageScreen to enhance
  - `../../opencode/packages/opencode/src/cli/cmd/tui/routes/session/index.tsx:900-1100` - TypeScript scroll navigation
  - `opencode_python/src/opencode_python/tui/keybindings.py` - Keybinding system to integrate with

  **API/Type References** (contracts to implement against):
  - `textual.containers.ScrollableContainer` - Scrollable container
  - `textual.reactive.watch_scroll_y` - Watch scroll position
  - `textual.widgets.Scrollbar` - Scrollbar widget

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual scrolling: https://textual.textualize.io/guide/widgets/scrollable-container/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for scroll examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `message_screen.py`: Existing MessageScreen to enhance
  - `session/index.tsx:900-1100`: Shows TypeScript scroll navigation patterns
  - `keybindings.py`: Shows keybinding system to add scroll commands to

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_message_screen_scroll.py
  - [ ] Test for page up/down keys
  - [ ] Test for half-page keys
  - [ ] Test for jump to first/last message
  - [ ] pytest tests/tui/test_message_screen_scroll.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] MessageScreen enhanced with scroll navigation
  - [ ] Page up/down (Ctrl+U/D) works
  - [ ] Half-page (Ctrl+B/F) works
  - [ ] Jump to first/last (G/Shift+G) works
  - [ ] pytest tests/tui/test_message_screen_scroll.py → PASS (all scroll tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_message_screen_scroll.py -v
  # Assert: Exit code 0
  # Assert: All scroll navigation tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing scroll navigation
  - [ ] Screenshots of message scroll behavior (optional)

  **Commit**: YES | NO (groups with 7, 8, 9)
  - Message: `feat(tui): add scroll navigation to MessageScreen`
  - Files: `opencode_python/src/opencode_python/tui/screens/message_screen.py`, `tests/tui/test_message_screen_scroll.py`
  - Pre-commit: `pytest tests/tui/test_message_screen_scroll.py`

---

- [x] 7. Implement Command Palette

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/dialogs/command_palette_dialog.py`
  - [x] Extend BaseDialog with SelectDialog
  - [x] Integrate with keybinding system (/ key to open)
  - [x] Display commands (session-list, model-select, theme-select, quit)
  - [x] Implement fuzzy search for commands (optional, basic search acceptable)
  - [x] Write tests for command palette and command execution

  **Must NOT do**:
  - [x] Do NOT implement slash commands in prompt yet (Phase 2+)
  - [x] Do NOT add complex command categories yet
  - [x] Do NOT implement command history yet (Phase 2+)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Command palette is moderate complexity UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (depends on task 0, 1)
  - **Blocks**: Tasks 8, 9, 10
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/component/dialog-command.tsx` - TypeScript command palette
  - `../../opencode/packages/opencode/src/cli/cmd/tui/context/keybind.tsx` - Keybinding matching logic
  - `opencode_python/src/opencode_python/tui/keybindings.py` - Keybinding system to integrate

  **API/Type References** (contracts to implement against):
  - `textual.widgets.Input` - Input widget for search
  - `textual.widgets.DataTable` - DataTable for command list

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual input: https://textual.textualize.io/guide/widgets/input/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for input examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `dialog-command.tsx`: Shows command palette UI pattern to adapt
  - `keybind.tsx`: Shows keybinding matching and execution logic
  - `keybindings.py`: Shows keybinding system to register command actions

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_command_palette.py
  - [ ] Test for command palette opening (/ key)
  - [ ] Test for command search and selection
  - [ ] Test for command execution
  - [ ] pytest tests/tui/test_command_palette.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] command_palette_dialog.py created with command list
  - [ ] / key opens command palette
  - [ ] Command search/filtering works
  - [ ] Command execution triggers actions
  - [ ] pytest tests/tui/test_command_palette.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_command_palette.py -v
  # Assert: Exit code 0
  # Assert: All command palette tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing command palette
  - [ ] Screenshots of command palette (optional)

  **Commit**: YES | NO (groups with 8, 9, 10)
  - Message: `feat(tui): implement command palette with essential commands`
  - Files: `opencode_python/src/opencode_python/tui/dialogs/command_palette_dialog.py`, `tests/tui/test_command_palette.py`
  - Pre-commit: `pytest tests/tui/test_command_palette.py`

---

### Wave 4: Polish

- [x] 8. Enhance Header (breadcrumbs, model display)

  **What to do**:
  - [x] Create `opencode_python/src/opencode_python/tui/widgets/header.py`
  - [x] Add breadcrumb navigation (parent session path)
  - [x] Add model display in header
  - [x] Add session title (read-only)
  - [x] Integrate with OpenCodeTUI app
  - [x] Write tests for header components

  **Must NOT do**:
  - [x] Do NOT implement session cycling yet (Phase 2+)
  - [x] Do NOT add agent indicator yet (Phase 2+)
  - [x] Do NOT implement complex status indicators yet

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Header enhancement is moderate complexity UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 9, 10)
  - **Blocks**: None (final integration task)
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/routes/session/header.tsx` - TypeScript header
  - `opencode_python/src/opencode_python/tui/app.py:93-97` - Existing header placeholder
  - `opencode_python/src/opencode_python/core/models.py` - Session model for data

  **API/Type References** (contracts to implement against):
  - `textual.widgets.Header` - Header widget from Textual
  - `textual.widgets.Label` - Label widget for text display
  - `opencode_python.core.models.Session` - Session model type

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual header: https://textual.textualize.io/guide/widgets/header/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for header examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `header.tsx`: Shows TypeScript header UI pattern to adapt
  - `app.py:93-97`: Shows existing header location and structure
  - `models.py`: Shows session model structure for data access

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_header.py
  - [ ] Test for breadcrumb display
  - [ ] Test for model display
  - [ ] Test for session title display
  - [ ] pytest tests/tui/test_header.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] header.py created with Header widget
  - [ ] Breadcrumbs display parent session path
  - [ ] Model display shows current model
  - [ ] Session title displayed
  - [ ] pytest tests/tui/test_header.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_header.py -v
  # Assert: Exit code 0
  # Assert: All header tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing header rendering
  - [ ] Screenshots of header (optional)

  **Commit**: YES | NO (groups with 9, 10)
  - Message: `feat(tui): create header widget with breadcrumbs and model display`
  - Files: `opencode_python/src/opencode_python/tui/widgets/header.py`, `tests/tui/test_header.py`
  - Pre-commit: `pytest tests/tui/test_header.py`

---

 - [x] 9. Enhance Footer (keyboard hints, status)

  **What to do**:
  - [ ] Create `opencode_python/src/opencode_python/tui/widgets/footer.py`
  - [ ] Add keyboard shortcut hints (q, /, Enter, Escape)
  - [ ] Add status messages (sync, pending messages)
  - [ ] Add metadata (tokens, cost, model)
  - [ ] Integrate with OpenCodeTUI app
  - [ ] Write tests for footer components

  **Must NOT do**:
  - [ ] Do NOT implement complex status indicators yet
  - [ ] Do NOT add version info yet (Phase 2+)
  - [ ] Do NOT implement interactive footer (read-only)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Footer enhancement is moderate complexity UI task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 8, 10)
  - **Blocks**: None (final integration task)
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/routes/session/footer.tsx` - TypeScript footer
  - `opencode_python/src/opencode_python/tui/app.py` - Existing Footer widget usage
  - `opencode_python/src/opencode_python/tui/keybindings.py` - Keybinding system to read hints from

  **API/Type References** (contracts to implement against):
  - `textual.widgets.Footer` - Footer widget from Textual
  - `textual.widgets.Static` - Static widget for hints

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual footer: https://textual.textualize.io/guide/widgets/footer/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for footer examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `footer.tsx`: Shows TypeScript footer UI pattern to adapt
  - `app.py`: Shows existing Footer usage in main app
  - `keybindings.py`: Shows keybinding definitions for hint display

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_footer.py
  - [ ] Test for keyboard hints display
  - [ ] Test for status messages
  - [ ] Test for metadata display
  - [ ] pytest tests/tui/test_footer.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] footer.py created with Footer widget
  - [ ] Keyboard hints displayed (q, /, Enter, Escape)
  - [ ] Status messages show sync/pending state
  - [ ] Metadata displays tokens/cost/model
  - [ ] pytest tests/tui/test_footer.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_footer.py -v
  # Assert: Exit code 0
  # Assert: All footer tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing footer rendering
  - [ ] Screenshots of footer (optional)

  **Commit**: YES | NO (groups with 10)
  - Message: `feat(tui): create footer widget with keyboard hints and status`
  - Files: `opencode_python/src/opencode_python/tui/widgets/footer.py`, `tests/tui/test_footer.py`
  - Pre-commit: `pytest tests/tui/test_footer.py`

---

 - [x] 10. Define 3 Essential Themes

  **What to do**:
  - [ ] Create `opencode_python/src/opencode_python/tui/themes/` directory
  - [ ] Define `light.tcss` theme with light colors
  - [ ] Define `dark.tcss` theme with dark colors
  - [ ] Define `dracula.tcss` theme with Dracula colors
  - [ ] Apply CSS variables for consistent theming
  - [ ] Write tests for theme application and color values

  **Must NOT do**:
  - [ ] Do NOT port all 30+ themes from TypeScript
  - [ ] Do NOT implement theme preview yet
  - [ ] Do NOT create custom theme editor yet

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-low`
    - Reason: Theme definition is straightforward CSS task
  - **Skills**: `[]`
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 8, 9)
  - **Blocks**: None (final integration task)
  - **Blocked By**: Task 0 (testing infrastructure), Task 1 (keybindings), Task 2 (dialogs)

  **References** (CRITICAL - Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `../../opencode/packages/opencode/src/cli/cmd/tui/context/theme.tsx:100-1200` - TypeScript theme definitions
  - `opencode_python/src/opencode_python/tui/app.py:42-59` - Existing CSS in app
  - Dracula theme reference: https://draculatheme.com/

  **API/Type References** (contracts to implement against):
  - `textual.app.App.CSS` - App CSS attribute
  - Textual CSS variables: `$primary`, `$secondary`, `$text`, etc.

  **Test References** (testing patterns to follow):
  - Existing test files in `tests/` (check structure)

  **Documentation References** (specs and requirements):
  - Textual CSS guide: https://textual.textualize.io/guide/css/
  - Textual styling: https://textual.textualize.io/guide/styling/

  **External References** (libraries and frameworks):
  - Textual repository: https://github.com/Textualize/textual (for CSS examples)

  **WHY Each Reference Matters** (explain the relevance):
  - `theme.tsx:100-1200`: Shows TypeScript theme definitions to adapt
  - `app.py:42-59`: Shows existing CSS structure in app
  - Dracula theme: Provides official color reference

  **Acceptance Criteria**:

  > **CRITICAL: AGENT-EXECUTABLE VERIFICATION ONLY**

  **TDD - RED Phase:**
  - [ ] Test file created: tests/tui/test_themes.py
  - [ ] Test for theme file existence
  - [ ] Test for theme application (CSS loads)
  - [ ] Test for color values (background, text, accent)
  - [ ] pytest tests/tui/test_themes.py → FAIL (no implementation)

  **TDD - GREEN Phase:**
  - [ ] themes/ directory created with 3 CSS files
  - [ ] light.tcss defined with light colors
  - [ ] dark.tcss defined with dark colors
  - [ ] dracula.tcss defined with Dracula colors
  - [ ] Themes apply correctly to app
  - [ ] pytest tests/tui/test_themes.py → PASS (all tests pass)

  **Automated Verification**:
  ```bash
  # Agent runs:
  pytest tests/tui/test_themes.py -v
  # Assert: Exit code 0
  # Assert: All theme tests pass
  ```

  **Evidence to Capture:**
  - [ ] Test output showing theme application
  - [ ] Screenshots of each theme (optional)

  **Commit**: YES | NO (groups with 8, 9)
  - Message: `feat(tui): define 3 essential themes (light, dark, dracula)`
  - Files: `opencode_python/src/opencode_python/tui/themes/light.tcss`, `opencode_python/src/opencode_python/tui/themes/dark.tcss`, `opencode_python/src/opencode_python/tui/themes/dracula.tcss`, `tests/tui/test_themes.py`
  - Pre-commit: `pytest tests/tui/test_themes.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0 | test(tui): setup TUI testing infrastructure | tests/conftest.py, tests/tui/test_app.py | pytest tests/tui/ |
| 1 | feat(tui): create keybinding system with essential shortcuts | tui/keybindings.py | pytest tests/tui/test_keybindings.py |
| 2 | feat(tui): create dialog infrastructure with base classes | tui/dialogs/__init__.py | pytest tests/tui/test_dialogs.py |
| 3 | feat(tui): create session list screen with DataTable | tui/screens/session_list_screen.py | pytest tests/tui/test_session_list_screen.py |
| 4 | feat(tui): create model select dialog | tui/dialogs/model_select_dialog.py | pytest tests/tui/test_model_select_dialog.py |
| 5 | feat(tui): create theme select dialog with 3 essential themes | tui/dialogs/theme_select_dialog.py | pytest tests/tui/test_theme_select_dialog.py |
| 6 | feat(tui): add scroll navigation to MessageScreen | tui/screens/message_screen.py | pytest tests/tui/test_message_screen_scroll.py |
| 7 | feat(tui): implement command palette with essential commands | tui/dialogs/command_palette_dialog.py | pytest tests/tui/test_command_palette.py |
| 8 | feat(tui): create header widget with breadcrumbs and model display | tui/widgets/header.py | pytest tests/tui/test_header.py |
| 9 | feat(tui): create footer widget with keyboard hints and status | tui/widgets/footer.py | pytest tests/tui/test_footer.py |
| 10 | feat(tui): define 3 essential themes (light, dark, dracula) | tui/themes/*.tcss | pytest tests/tui/test_themes.py |

---

## Success Criteria

### Verification Commands
```bash
# Run all TUI tests
pytest tests/tui/ -v --cov=opencode_python/src/opencode_python/tui --cov-report=term-missing

# Verify TUI launches
opencode tui
# Expected: TUI opens with session list

# Manual QA Checklist
- [ ] Launch TUI: `opencode tui`
- [ ] See session list
- [ ] Select session with Enter
- [ ] See message timeline
- [ ] Scroll messages with arrows, Ctrl+U/D, Ctrl+B/F
- [ ] Jump to first/last message with G/Shift+G
- [ ] Type message in prompt
- [ ] Submit message with Enter
- [ ] See new message in timeline
- [ ] Press '/' to open command palette
- [ ] Select "switch theme" command
- [ ] Select new theme
- [ ] Verify theme changed
- [ ] Press 'q' to quit
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (pytest tests/tui/)
- [ ] Manual QA checklist verified
- [ ] Code follows Textual idioms (not provider pattern)
- [ ] TDD workflow followed for all tasks

---

## Post-Plan Notes

### Phase 2+ Considerations
This plan covers **Phase 1 (Core Workflows)** only. Future phases will address:
- Autocomplete for prompt input
- Command history (up/down arrows)
- Prompt stash
- Frecency tracking
- Additional themes (beyond 3 essentials)
- Additional dialogs (model provider, status, MCP, etc.)
- Advanced keyboard shortcuts
- Animations and polish
- Performance optimization

### Architecture Decisions Made
- **No provider/context pattern**: Using Textual's reactive system instead
- **No custom dialog system**: Using Textual's ModalScreen instead
- **No custom TUI framework**: Using standard Textual widgets
- **CSS-based theming**: Using Textual's CSS variables instead of theme objects
- **Screen-based routing**: Using Textual's screen stack instead of custom router

### Testing Infrastructure Established
- **pytest-asyncio**: For async Textual app testing
- **Widget tests**: For component-level testing
- **Manual QA checklist**: For full TUI verification
- **TDD workflow**: RED → GREEN → REFACTOR for all tasks
