# ULTRAWORK STATUS - TUI Epics Implementation

## Rules of Engagement

### Isolation Model
- **Event-driven integration**: Use `opencode_python/src/opencode_python/core/event_bus.py` for cross-epic communication
- **Plugin-style extensions**: Each epic adds new modules under its domain package
- **Minimal hotspot edits**: When hotspots must be touched, add only what's needed
- **Conflict posture**: Conflicts expected in Wave 4; resolve via integration worktree
- **Safety**: No remote history rewrite; use merge commits for integration

### Epic Worktree Conventions

- Base branch: `main` (wt/tui is current worktree)
- Branch naming: `epic/<slug>`
- Worktree path: `./.worktrees/<slug>`
- Commit message format: `epic(<slug>): <short summary>`

### TUI Framework

- **Textual 7.4.0** is authoritative (no Rich-only migration)
- Rich is used for formatting only, not as TUI framework

## Integration Contract

### Hotspot Files (Edit Only When Unavoidable)

These files are high-risk collision points. Single-touch only, document every edit.

| File | Primary Owner(s) | Notes |
|------|------------------|-------|
| `opencode_python/src/opencode_python/tui/app.py` | Epic 1, Epic 7 | Register screens/bindings only |
| `opencode_python/src/opencode_python/core/models.py` | Epic 3, Epic 4 | Session model has `extra="forbid"` |
| `opencode_python/src/opencode_python/core/session.py` | Epic 3, Epic 6 | SessionManager API |
| `opencode_python/src/opencode_python/core/settings.py` | Epic 2, Epic 4, Epic 6, Epic 7, Epic 8 | Add settings keys only |
| `opencode_python/src/opencode_python/core/event_bus.py` | Epic 3, Epic 4, Epic 6, Epic 8 | Primary integration point |
| `opencode_python/src/opencode_python/storage/store.py` | Epic 3, Epic 6, Epic 8 | Use separate storage namespaces |
| `opencode_python/src/opencode_python/tui/keybindings.py` | Epic 1, Epic 7 | Coordinate keybinding additions |
| `opencode_python/src/opencode_python/tui/screens/__init__.py` | Epic 2, Epic 7, Epic 8 | Screen ownership TBD |
| `opencode_python/src/opencode_python/tui/screens/theme_settings_screen.py` | Epic 7 | Theme settings screen with live preview |
| `opencode_python/src/opencode_python/tui/screens/keybinding_editor_screen.py` | Epic 7 | Keybinding editor with conflict detection |
| `opencode_python/src/opencode_python/themes/models.py` | Epic 7 | Theme models (Theme, ThemeMetadata, ThemeSettings, DensityMode) |
| `opencode_python/src/opencode_python/themes/loader.py` | Epic 7 | Theme loader for YAML and TCSS files |
| `opencode_python/src/opencode_python/themes/events.py` | Epic 7 | Theme and keybinding events |
| `opencode_python/src/opencode_python/themes/dark.yaml` | Epic 7 | Dark theme YAML configuration |
| `opencode_python/src/opencode_python/themes/light.yaml` | Epic 7 | Light theme YAML configuration |
| `opencode_python/src/opencode_python/themes/high-contrast.yaml` | Epic 7 | High contrast theme YAML configuration |

### Medium-Risk Shared Points

File | Owner Epics | Notes |
|------|--------------|-------|
| `opencode_python/src/opencode_python/tui/dialogs/command_palette_dialog.py` | Epic 1 | Command palette dialog |
| `opencode_python/src/opencode_python/tui/dialogs/theme_select_dialog.py` | Epic 2, Epic 7 | Theme selection dialog |
| `opencode_python/src/opencode_python/tui/dialogs/model_select_dialog.py` | Epic 2, Epic 4, Epic 7 | Model selection dialog |

### Integration Rules

1. Prefer new modules under domain packages:
   - `opencode_python/src/opencode_python/providers/` (Epic 2)
   - `opencode_python/src/opencode_python/skills/` (Epic 5)
   - `opencode_python/src/opencode_python/tools/` (Epic 6)
   - `opencode_python/src/opencode_python/storage/` (Epic 3, Epic 6, Epic 8)
   - `opencode_python/src/opencode_python/observability/` (Epic 8)
   - `opencode_python/src/opencode_python/themes/` (Epic 7)

2. Register via:
   - Events in `opencode_python/src/opencode_python/core/event_bus.py` (primary)
   - Registry patterns for tools/skills/providers

3. Do NOT extend `Session` model in `opencode_python/src/opencode_python/core/models.py` unless absolutely required. Store epic-specific metadata under new storage namespaces instead.

4. Register screens in `opencode_python/src/opencode_python/tui/screens/__init__.py`

5. Settings defaults should be additive in `opencode_python/src/opencode_python/core/settings.py` (additive only, no breaking changes)

### Event Namespace Registry

Each epic declares event names it emits/subscribes to. Prevents duplicate semantics.

| Epic | Emits | Subscribes To |
|------|-------|----------------|
| Epic 1 (Shell/Nav) | `screen:change`, `command:execute`, `palette:open` | `session:created`, `provider:changed`, `account:changed` | All screen events (observer pattern) |
| Epic 2 (Providers) | `provider:created`, `provider:updated`, `provider:deleted`, `provider:test`, `account:created`, `account:updated`, `account:deleted`, `account:active` | `session:start`, `tool:execute` | All provider events |
| Epic 3 (Sessions) | `session:created`, `session:updated`, `session:deleted`, `session:resumed`, `session:autosave`, `session:export` | `screen:change`, `agent:execute`, `tool:execute` | Session creation with validation, auto-save, resume exactly, export MD/JSON with redaction implemented |
| Epic 4 (Agents) | `agent:profile:select`, `agent:config:update`, `agent:execute`, `agent:complete` | `session:start`, `skill:enable`, `tool:execute` | Profile selection, prerequisite checking, per-session config (model/temp/budget), audit trail |
| Epic 5 (Skills) | `skill:enable`, `skill:disable`, `skill:block`, `skill:execute` | `agent:execute`, `session:start`, `skill:enable` | Skills enable/disable, runtime blocking, and contracts implemented |
| Epic 6 (Tools) | `tool:discover`, `tool:allow`, `tool:deny`, `tool:execute`, `tool:log` | `session:start`, `skill:enable`, `agent:execute` | Tool discovery panel, allow/deny workflow, execution log with diffs |
| Epic 7 (Themes/UX) | `theme:change`, `keybinding:update`, `layout:toggle` | All screen events (observer pattern) | theme system, keybindings, density | Implement ThemeManager |

### Epic Tracking Table

| Epic | Slug | Branch | Worktree Path | Status | Last Update | Key Files Changed | Notes |
|------|-------|--------|---------------|---------|-------------|------------------|--------|------------|
| Epic 1 | `tui-shell-navigation` | `epic/tui-shell-navigation` | `./.worktrees/tui-shell-navigation` | Done | 2026-01-30 12:15:00 | Home screen, command palette, custom events | tui/screens/home_screen.py, tui/palette/command_palette.py, tui/app.py (minimal), tests/tui/test_home_screen.py |
| Epic 2 | `providers-accounts` | `epic/providers-accounts` | `./.worktrees/providers-accounts` | Done | 2026-01-30 11:31:00 | opencode_python/src/opencode_python/providers_mgmt/, opencode_python/src/opencode_python/tui/screens/provider_settings_screen.py, opencode_python/src/opencode_python/tui/screens/account_settings_screen.py, opencode_python/src/opencode_python/tui/dialogs/provider_edit_dialog.py, opencode_python/src/opencode_python/tui/dialogs/account_edit_dialog.py, opencode_python/src/opencode_python/core/settings.py, tests/test_providers_models.py, tests/test_providers_storage.py | Provider CRUD, test connection, secure credential storage, active account switching | Provider and Account models with Pydantic, ProviderStorage and AccountStorage classes, provider/account TUI screens, event emission for provider/account changes, secure API key hashing with SHA-256 |
| Epic 3 | `sessions` | `epic/sessions` | `./.worktrees/sessions` | Done | 2026-01-30 12:00:00 | storage/session_meta.py, core/session.py, export/session_exporter.py, tui/screens/session_creation_screen.py, tui/widgets/save_indicator.py | Session creation with validation, auto-save, resume exactly, export MD/JSON with redaction implemented | - |
| Epic 4 | `agents` | `epic/agents` | `./.worktrees/agents` | Done | 2026-01-30 11:45:00 | agents/ package, core/settings.py (minimal) | Profile selection, prerequisite checking, per-session config (model/temp/budget), audit trail | - |
| Epic 5 | `skills` | `epic/skills` | `./.worktrees/skills` | Planned | 2026-01-30 12:20:00 | None yet | Skills enable/disable, runtime blocking, and contracts implemented | - |
| Epic 6 | `tools` | `epic/tools` | `./.worktrees/tools` | Done | 2026-01-30 11:50:00 | opencode_python/src/opencode_python/tools/, opencode_python/src/opencode_python/tui/screens/{tools_panel_screen.py,tool_log_viewer_screen.py}, tests/test_tool_permission.py, tests/test_tool_execution_log.py | Tool discovery panel, allow/deny workflow, execution log with diffs | ToolPermissionSystem implemented |
| Epic 7 | `themes-ux` | `epic/themes-ux` | `./.worktrees/themes-ux` | Done | 2026-01-30 12:30:00 | theme system, keybindings, density | Implement ThemeManager |

---

## Requirements Staging

### Epic 1 - TUI Shell & Navigation

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 1.1 — Launch & Home**
- On launch, show home screen with active provider/account, recent sessions, and quick actions
- Actions: "New Session", "Resume Session", "Settings"
- Resume recent session loads session state from storage

**Story 1.2 — Global command palette**
- Command palette accessible from anywhere (Ctrl+P)
- Actions: execute commands, open settings

### Epic 2 - Providers & Accounts

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 2.1 — Provider management**
- Create, update, delete providers
- Switch active provider

**Story 2.2 — Account management**
- Create, update, delete accounts
- Switch active account

### Epic 3 - Sessions

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 3.1 — Session storage**
- Persistent session storage with metadata

**Story 3.2 — Session creation**
- Create new session with validation

### Epic 4 - Agents

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 4.1 — Agent profile management**
- Profile selection and configuration

### Epic 5 - Skills

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 5.1 — Skill registration**
- Skills enable/disable functionality

### Epic 6 - Tools

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 6.1 — Tool permission system**
- Allow/deny tool execution

### Epic 7 - Themes & UX

**Acceptance Criteria (from TUI_EPICS_ONE.md):**

**Story 7.1 — Theme selection**
- As a developer, I want to switch themes (dark/light/high-contrast) and font/layout density, so the TUI fits my environment.

**Feature: Themes**
  Scenario: Change theme
    Given I am in Appearance Settings
    When I select "High Contrast"
    Then the UI should update immediately
    And the theme should persist after restart

**Story 7.2 — Keybindings**
- As a developer, I want configurable keybindings, so I can optimize my workflow.

**Feature: Keybindings**
  Scenario: Rebind an action
    Given I am in Keybinding Settings
    When I bind "Open command palette" to "Ctrl+P"
    Then "Ctrl+P" should open the command palette
    And conflicts should be detected and displayed

  Scenario: Restore defaults
    Given I customized keybindings
    When I select "Restore defaults"
    Then keybindings should revert to default mappings

**Story 7.3 — Accessibility (Reduced Motion)**
- As a developer, I want accessibility-friendly defaults, so the UI doesn't overwhelm me.

**Feature: Themes**
  Scenario: Accessibility-friendly defaults
    Given I enable "Reduced motion"
    When transitions would normally animate
    Then animations should be disabled

**Story 7.4 — Density modes**
- As a developer, I want to control spacing to optimize for my screen size and readability.

**Implementation:**
- Theme system with YAML configuration
- Theme loader supporting both YAML and TCSS files
- Theme models with Pydantic validation
- Theme settings screen with live preview
- Extended keybindings system with custom storage
- Keybinding editor screen with conflict detection
- Density modes: compact, normal, expanded
- Reduced motion toggle for accessibility
- Events: theme:change, keybinding:update, layout:toggle
- Hot reload support
