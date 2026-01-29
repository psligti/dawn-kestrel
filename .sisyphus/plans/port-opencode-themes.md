# Port OpenCode Themes to opencode_python

## TL;DR

> **Quick Summary**: Port 6 popular themes from opencode (dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro) to opencode_python as Pydantic models with Textual (TUI) and Rich (CLI) integration, plus auto-detect system dark/light mode using darkdetect.
>
> **Deliverables**:
> - 6 theme JSON files converted to Python Pydantic models
> - Theme loader module for discovery and loading
> - Textual CSS variable mapping for TUI theming
> - Rich Theme object mapping for CLI styling
> - Settings integration (tui_theme with "auto" mode)
> - System dark/light mode detection with fallback to dracula-dark
> - Test suite with 90%+ coverage of theme functionality
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Settings extension → Theme models → Textual/Rich integration → Tests

---

## Context

### Original Request

User wants to "use the design and themes from opencode dir and port them into opencode_python".

### Interview Summary

**Key Discussions**:
- **Theme selection**: Port 6 popular themes (not all 18) - dracula (default), gruvbox, catppuccin, nord, tokyonight, onedarkpro
- **Configuration**: Settings file + auto-detect system dark/light mode (darkdetect library)
- **UI frameworks**: Both Textual (TUI) and Rich (CLI) must support the same themes
- **Test strategy**: Tests after implementation (pytest, pytest-asyncio)
- **Scope boundaries**: Explicitly exclude custom themes, runtime hot-swap, theme editor, accessibility validation

**Technical Decisions**:
- Convert JSON themes to Pydantic models for type safety
- Single source of truth for theme definitions
- Theme selection is startup-time only (restart required to change themes)
- Auto-detect system mode with fallback to dracula-dark when darkdetect returns None
- Settings extension: add fields to existing Pydantic Settings class

### Research Findings

**From opencode theme structure analysis**:
- All themes follow consistent structure: metadata, light/dark modes
- **Seeds** (9 base colors): neutral, primary, success, warning, error, info, interactive, diffAdd, diffDelete
- **Overrides** (50+ color tokens): backgrounds, borders (weak/base/strong + states), surfaces, text, syntax, markdown

**From Textual theming patterns**:
- Theme dataclass with required fields: name, primary, secondary, dark, foreground, background, surface, panel
- CSS variables support via `variables` dict
- Theme registration with `app.register_theme()` before use
- Reactive `app.theme` property for switching
- Built-in themes: nord, gruvbox, tokyo-night (reference implementation)

**From Rich theming patterns**:
- Theme class with styles as dict mapping
- Style objects and Style.parse() for dynamic colors
- use_theme() context manager for temporary themes
- push_theme() / pop_theme() for manual stack management
- Supports hex, RGB, ANSI colors
- Can load from INI config files

**From opencode_python settings exploration**:
- Existing Pydantic Settings with pydantic-settings
- Environment variable prefix: `OPENCODE_PYTHON_`
- `.env` file support in working directory
- Singleton pattern with `get_settings()`
- `tui_theme: str = Field(default="auto")` already exists but not used
- Config directory: `~/.config/opencode-python/`
- Storage directory: `~/.local/share/opencode-python/`

**From darkdetect research**:
- Library: `darkdetect` (albertosottile/darkdetect on GitHub)
- Supports: macOS 10.14+, Windows 10+, Linux (variable by DE)
- Returns: `"Light"`, `"Dark"`, or `None` (SSH/headless)
- Installation: `pip install darkdetect`

### Metis Review

**Identified Gaps** (addressed in plan):
1. **Scope creep risk**: opencode has 50+ color tokens per theme. **Guardrail**: Define minimum required tokens (max 25) and only port those.
2. **Theme priority**: What if user sets manual theme AND auto-detect suggests different? **Resolution**: Manual override wins (settings file takes precedence).
3. **Missing theme modes**: What if theme only has dark mode but system is light? **Resolution**: All 6 themes have both light and dark modes verified.
4. **Runtime switching**: Hot-swap vs restart-only? **Decision**: Startup-time only (restart required) - simpler, within scope.
5. **Custom themes**: Support user-defined themes? **Decision**: Explicitly excluded from scope (future work).
6. **Theme validation**: Malformed theme files? **Resolution**: Validate on load, fail with clear error message.
7. **Fallback strategy**: darkdetect returns None? **Resolution**: Default to dracula-dark.
8. **CSS variable mapping**: How to map generic theme colors to Textual variables? **Resolution**: Define explicit mapping in theme loader module.
9. **Rich vs Textual divergence**: Can they use different colors? **Decision**: No - identical colors from single source.
10. **Accessibility**: WCAG contrast checks? **Decision**: Excluded from scope (user responsibility).

**Guardrails Applied**:
- NO porting all 50+ override tokens (only minimum required)
- NO runtime theme switching (startup-time only)
- NO custom user-defined themes
- NO theme editor/preview UI
- NO theme auto-generation (light ↔ dark)
- NO accessibility validation (contrast ratios, color blindness)
- NO per-framework theme divergence (Rich and Textual share colors)

---

## Work Objectives

### Core Objective

Implement a theme system for opencode_python that ports 6 popular themes from opencode, supporting both Textual TUI and Rich CLI with auto-detection of system dark/light mode.

### Concrete Deliverables

1. **Theme Pydantic models**: `src/opencode_python/theme/models.py` - define theme data structures
2. **Theme JSON files**: `src/opencode_python/theme/themes/*.json` - 6 converted theme files (dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro)
3. **Theme loader module**: `src/opencode_python/theme/loader.py` - discovery, loading, validation
4. **Textual CSS generator**: `src/opencode_python/theme/textual_adapter.py` - generate CSS variables from themes
5. **Rich Theme adapter**: `src/opencode_python/theme/rich_adapter.py` - create Rich Theme objects
6. **Settings integration**: Extend `src/opencode_python/core/settings.py` with theme configuration fields
7. **TUI theme application**: Update `src/opencode_python/tui/app.py` to load and apply themes
8. **Test suite**: `tests/test_theme.py` - comprehensive test coverage (90%+)
9. **Documentation**: `THEME.md` - how to configure and use themes

### Definition of Done

- [ ] All 6 theme JSON files are valid Pydantic models
- [ ] Theme loader can discover and load all themes
- [ ] Textual TUI applies theme colors via CSS variables
- [ ] Rich CLI applies theme colors via Theme objects
- [ ] Settings support `tui_theme="auto"` with darkdetect integration
- [ ] Settings support explicit theme names (e.g., `tui_theme="gruvbox"`)
- [ ] Fallback to dracula-dark when darkdetect returns None
- [ ] All tests pass with 90%+ coverage
- [ ] Documentation exists for configuration

### Must Have

- 6 themes ported: dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro
- Default theme: dracula-dark (when system in dark mode or darkdetect fails)
- Auto-detect system dark/light mode using darkdetect
- Settings file configuration (environment variables + .env file)
- Both Textual and Rich support same theme colors
- Startup-time theme loading (no runtime hot-swap required)
- Clear error messages for invalid themes
- Test coverage of theme loading, validation, CSS generation, and application

### Must NOT Have (Guardrails)

**Scope Exclusions** (explicitly NOT building):
- NO porting all 50+ override tokens from opencode themes
- Only port minimum required tokens (max 25 per theme)
- NO runtime theme switching (restart required to change themes)
- NO custom user-defined themes
- NO theme editor, preview, or UI controls for theme selection
- NO theme auto-generation (light → dark inversion, dark → light inversion)
- NO accessibility validation (WCAG contrast ratios, color blindness support)
- NO per-framework theme divergence (Rich and Textual share identical colors)
- NO theme variants (e.g., catppuccin-latte, catppuccin-frappe)
- NO Rich-style theme file loading (INI format) - use JSON only
- NO dynamic CSS injection beyond Textual variable system

**AI Slop Patterns to Avoid**:
- Over-validation: Adding contrast ratio checks, color blindness mode, etc.
- Premature abstraction: Creating base classes for "future extensibility"
- Scope inflation: Porting border-focus, border-active, etc. when only border is needed
- Documentation bloat: Adding extensive examples for every widget styling
- Feature creep: "Let's add theme command", "Let's add theme preview", etc.

---

## Verification Strategy

### Test Decision

- **Infrastructure exists**: YES (pytest, pytest-asyncio already in pyproject.toml)
- **User wants tests**: YES (Tests after implementation)
- **Framework**: pytest with pytest-asyncio
- **Coverage goal**: 90%+ of theme-related code

### Automated Verification (Agent-Executable)

Each TODO includes executable verification procedures. No steps like "user manually tests..." or "user visually confirms..." are used.

**Verification by Deliverable Type**:

| Type | Verification Tool | Procedure |
|--------|------------------|-------------|
| **Pydantic Models** | pytest | Model validation, JSON parsing, type checking |
| **Theme Loader** | pytest | Discovery, loading, validation, fallback logic |
| **Textual CSS** | pytest | CSS variable generation, syntax validation |
| **Rich Theme** | pytest | Theme object creation, color mapping |
| **Settings Integration** | pytest | Environment variable loading, .env parsing, defaults |
| **TUI Application** | pytest + Bash | Run TUI, capture CSS variables, verify theme applied |
| **CLI Output** | pytest + Bash | Run CLI with Rich, capture output, verify colors |
| **Documentation** | pytest + read | Documentation file exists and is valid markdown |

**Evidence Requirements**:
- Test output captured and compared against expected values
- CSS variables asserted to match theme definitions
- Console output verified to use theme colors
- Settings values validated to be correct
- Error messages tested for invalid inputs

---

## Execution Strategy

### Parallel Execution Waves

**Wave 1** (Start Immediately):
- Task 1: Create theme Pydantic models (no dependencies)
- Task 2: Port 6 theme JSON files (no dependencies)
- Task 3: Add darkdetect to dependencies

**Wave 2** (After Wave 1):
- Task 4: Create theme loader module (depends: Task 1, 2)
- Task 5: Extend settings with theme fields (depends: Task 4)
- Task 6: Create Textual CSS adapter (depends: Task 1, 4)

**Wave 3** (After Wave 2):
- Task 7: Create Rich Theme adapter (depends: Task 1, 4)
- Task 8: Update TUI app to use themes (depends: Task 5, 6)
- Task 9: Write comprehensive test suite (depends: Task 4, 6, 7, 8)

**Critical Path**: Task 1 → Task 4 → Task 8 → Task 9
**Parallel Speedup**: ~50% faster than sequential (3 independent tasks in Wave 1)

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|-------|-------------|--------|---------------------|
| 1 | None | 4, 6, 7 | 2, 3 |
| 2 | None | 4 | 1, 3 |
| 3 | None | 4 | 1, 2 |
| 4 | 1, 2 | 5, 6, 7 | None (sequential) |
| 5 | 4 | 8 | 6, 7 |
| 6 | 1, 4 | 8 | 5, 7 |
| 7 | 1, 4 | None (sequential) | 5, 6 |
| 8 | 5, 6 | 9 | 7 |
| 9 | 4, 6, 7, 8 | None (final) | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|-------|---------|-------------------|
| 1 | 1, 2, 3 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) × 3 |
| 2 | 4, 5, 6 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) × 3 |
| 3 | 7, 8, 9 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=true) × 3 |

---

## TODOs

- [ ] 1. Create theme Pydantic models

  **What to do**:
  - Create `src/opencode_python/theme/models.py`
  - Define `ThemeSeedColors` model with 9 seed colors (neutral, primary, success, warning, error, info, interactive, diffAdd, diffDelete)
  - Define `ThemeVariant` model with seeds and overrides
  - Define `Theme` model with name, id, light, dark variants
  - Add Pydantic validation for hex color format (regex: `^#[0-9a-fA-F]{6}$`)
  - Add docstrings and type hints

  **Must NOT do**:
  - Don't include all 50+ override tokens yet (minimum tokens only in this task)
  - Don't create base classes for extensibility
  - Don't add JSON serialization yet (theme files handle this separately)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple model definitions, low complexity
  - **Skills**: `[]`
    - No specific skills needed for Pydantic model creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Task 4 (theme loader needs models)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/core/models.py` - Pydantic model patterns used in codebase
  - `opencode_python/src/opencode_python/core/settings.py` - Pydantic settings patterns (Field, validator usage)
  - `opencode/packages/ui/src/theme/types.ts` - TypeScript type definitions to mirror structure

  **API/Type References** (contracts to implement against):
  - `opencode/packages/ui/src/theme/types.ts:ThemeSeedColors` - Seed color structure (9 colors)
  - `opencode/packages/ui/src/theme/types.ts:ThemeVariant` - Light/dark variant structure
  - `opencode/packages/ui/src/theme/types.ts:DesktopTheme` - Full theme structure with metadata

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/test_export_import.py` - Pydantic model testing patterns
  - Test model validation, JSON parsing, type checking patterns

  **Documentation References** (specs and requirements):
  - Pydantic documentation: https://docs.pydantic.dev/latest/concepts/models/ - Field, validator usage
  - Hex color regex: `^#(?:[0-9a-fA-F]{3}){1,2}$`

  **External References** (libraries and frameworks):
  - Pydantic docs: https://docs.pydantic.dev/latest/ - Model validation
  - Python typing: https://docs.python.org/3/library/typing.html - Type hints

  **WHY Each Reference Matters** (explain the relevance):
  - `opencode_python/src/opencode_python/core/models.py`: Shows existing Pydantic patterns for consistency (Field aliases, validators)
  - `opencode/packages/ui/src/theme/types.ts`: TypeScript source structure - port identical structure to Python
  - Pydantic docs: API reference for model definition syntax
  - Hex color regex: Ensures valid hex codes in theme files

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_theme_models.py
  - [ ] Test covers: valid hex codes accepted, invalid hex codes rejected
  - [ ] Test covers: ThemeSeedColors with all 9 fields validated
  - [ ] Test covers: Theme with light/dark variants
  - [ ] pytest tests/test_theme_models.py → PASS (5+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "from src.opencode_python.theme.models import Theme, ThemeSeedColors; print('Models imported successfully')"
  # Assert: Output is "Models imported successfully" with no errors
  ```

  **Evidence to Capture**:
  - [ ] Python import output (no ImportError or ValidationError)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 2)
  - Message: `feat(theme): add Pydantic theme models`
  - Files: `src/opencode_python/theme/models.py`

---

- [ ] 2. Port 6 theme JSON files

  **What to do**:
  - Convert opencode JSON themes to Python format
  - Create `src/opencode_python/theme/themes/` directory
  - Port these 6 themes: dracula.json, gruvbox.json, catppuccin.json, nord.json, tokyonight.json, onedarkpro.json
  - Each theme has: name, id, light (seeds + overrides), dark (seeds + overrides)
  - **CRITICAL**: Only port MINIMUM tokens (max 25 per theme):
    - Seeds (9): neutral, primary, success, warning, error, info, interactive, diffAdd, diffDelete
    - Overrides (max 16): background-base, background-stronger, border-base, text-base, text-strong, text-weak, syntax-string, syntax-primitive, syntax-property, syntax-type, markdown-heading, markdown-text, markdown-code
    - Total: 25 tokens per theme (9 seeds + 16 overrides)
  - Remove all other override tokens from opencode (border-focus, border-hover, etc.)
  - Verify hex codes are valid
  - Keep light/dark mode structure

  **Must NOT do**:
  - Don't port all 50+ override tokens
  - Don't add extra tokens not in minimum list
  - Don't create theme variants (e.g., gruvbox-light.json)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: File conversion, straightforward data transformation
  - **Skills**: `[]`
    - No specific skills needed for JSON file conversion

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 4 (theme loader needs theme files)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode/packages/ui/src/theme/themes/dracula.json` - Example theme structure (read to understand format)
  - `opencode/packages/ui/src/theme/themes/gruvbox.json` - Example theme structure
  - `opencode/packages/ui/src/theme/themes/catppuccin.json` - Example theme structure
  - `opencode/packages/ui/src/theme/themes/nord.json` - Example theme structure
  - `opencode/packages/ui/src/theme/themes/tokyonight.json` - Example theme structure
  - `opencode/packages/ui/src/theme/themes/onedarkpro.json` - Example theme structure

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/theme/models.py` - Pydantic Theme models (use these as template)
  - Theme structure must match: name, id, light (seeds + overrides), dark (seeds + overrides)

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/test_export_import.py` - File loading and validation patterns

  **Documentation References** (specs and requirements):
  - Theme files location: `opencode/packages/ui/src/theme/themes/*.json` - Source files to convert
  - Minimum token list defined in plan (this section)

  **External References** (libraries and frameworks):
  - JSON schema validation: https://json-schema.org/ - Ensure valid JSON format

  **WHY Each Reference Matters** (explain the relevance):
  - Source JSON files: Direct input for conversion, must preserve structure
  - Pydantic models: Target format for converted data
  - JSON schema: Validates JSON syntax before conversion

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_theme_files.py
  - [ ] Test covers: all 6 themes load successfully
  - [ ] Test covers: each theme has required fields (name, id, light, dark)
  - [ ] Test covers: hex codes are valid
  - [ ] Test covers: minimum token count (25 max)
  - [ ] pytest tests/test_theme_files.py → PASS (6+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  import json
  from src.opencode_python.theme.loader import load_theme

  for theme_name in ['dracula', 'gruvbox', 'catppuccin', 'nord', 'tokyonight', 'onedarkpro']:
      theme = load_theme(theme_name)
      assert theme is not None, f'Theme {theme_name} failed to load'
      assert theme.name == theme_name, f'Theme {theme_name} has wrong name'
      print(f'{theme_name}: OK')
  print('All themes loaded successfully')
  "
  # Assert: Output is "All themes loaded successfully"
  ```

  **Evidence to Capture**:
  - [ ] Python script output (each theme loaded)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 1)
  - Message: `feat(theme): port 6 themes from opencode`
  - Files: `src/opencode_python/theme/themes/*.json`

---

- [ ] 3. Add darkdetect dependency

  **What to do**:
  - Add `darkdetect>=0.2.0` to `opencode_python/pyproject.toml`
  - Verify darkdetect supports target platforms (macOS 10.14+, Windows 10+, Linux)

  **Must NOT do**:
  - Don't use alternative detection methods
  - Don't add platform-specific fallback logic here (handled in loader)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple dependency addition to pyproject.toml
  - **Skills**: `[]`
    - No specific skills needed for dependency management

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: None (no dependencies)
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/pyproject.toml` - Existing dependency format (dependencies section)
  - Other dependencies in pyproject.toml: See pydantic-settings, textual, rich formats

  **API/Type References** (contracts to implement against):
  - None (just follow existing dependency format)

  **Test References** (testing patterns to follow):
  - None (dependency addition doesn't require tests)

  **Documentation References** (specs and requirements):
  - darkdetect GitHub: https://github.com/albertosottile/darkdetect - Installation and API reference
  - darkdetect PyPI: https://pypi.org/project/darkdetect/ - Version info, platform support

  **External References** (libraries and frameworks):
  - darkdetect docs: Library installation and usage

  **WHY Each Reference Matters** (explain the relevance):
  - pyproject.toml: Target file for modification
  - darkdetect docs: Verify library capabilities and installation
  - Existing dependencies: Follow same format for consistency

  **Acceptance Criteria** (Agent-Executable Verification):

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  uv pip install darkdetect
  python -c "import darkdetect; print(f'darkdetect {darkdetect.__version__} installed')"
  # Assert: Output contains darkdetect version
  ```

  **Evidence to Capture**:
  - [ ] uv pip install output
  - [ ] Python import output (version info)

  **Commit**: YES | NO (groups with 1, 2)
  - Message: `chore(deps): add darkdetect for system theme detection`
  - Files: `pyproject.toml`

---

- [ ] 4. Create theme loader module

  **What to do**:
  - Create `src/opencode_python/theme/loader.py`
  - Implement `load_theme(theme_name: str) -> Theme | None`
  - Implement `get_available_themes() -> List[str]`
  - Implement `resolve_theme(settings: Settings) -> Theme` (handles "auto" mode)
  - Implement system dark/light mode detection using darkdetect
  - Implement fallback to dracula-dark when darkdetect returns None
  - Add validation: theme name must be valid, hex codes valid
  - Add error handling: clear messages for invalid theme files
  - Map theme colors to internal token structure (9 seeds + 16 overrides)

  **Must NOT do**:
  - Don't support runtime hot-swapping
  - Don't load themes from user directories (only bundled themes)
  - Don't auto-generate missing light/dark variants
  - Don't create theme preview functionality

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Standard Python module with file I/O and validation
  - **Skills**: `[]`
    - No specific skills needed for loader implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Tasks 5, 6)
  - **Blocks**: Task 5 (settings needs loader), Task 6 (adapter needs loader)
  - **Blocked By**: Task 1 (models), Task 2 (theme files), Task 3 (darkdetect)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/core/settings.py:get_settings()` - Settings loading pattern (singleton)
  - `opencode/packages/ui/src/theme/resolve.ts` - Theme resolution logic (from opencode)

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/theme/models.py` - Theme Pydantic models (use for validation)
  - `src/opencode_python/core/settings.py:Settings` - Settings object (read tui_theme field)

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/test_export_import.py` - Error handling patterns

  **Documentation References** (specs and requirements):
  - darkdetect docs: https://github.com/albertosottile/darkdetect - API usage
  - Settings extension plan: Tasks 5, 6

  **External References** (libraries and frameworks):
  - Python pathlib: https://docs.python.org/3/library/pathlib.html - File operations

  **WHY Each Reference Matters** (explain the relevance):
  - settings.py: Show settings loading pattern for tui_theme field
  - models.py: Pydantic models for theme validation
  - darkdetect docs: API for system theme detection

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_theme_loader.py
  - [ ] Test covers: load_theme() returns valid theme
  - [ ] Test covers: load_theme() returns None for invalid theme
  - [ ] Test covers: resolve_theme() with "auto" detects system dark/light
  - [ ] Test covers: resolve_theme() with explicit theme name returns that theme
  - [ ] Test covers: fallback to dracula-dark when darkdetect returns None
  - [ ] Test covers: get_available_themes() returns 6 themes
  - [ ] pytest tests/test_theme_loader.py → PASS (8+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  from opencode_python.theme.loader import get_available_themes, resolve_theme
  from opencode_python.core.settings import Settings

  # Test get_available_themes
  themes = get_available_themes()
  assert len(themes) == 6, f'Expected 6 themes, got {len(themes)}'
  print(f'Available themes: {themes}')

  # Test resolve_theme with auto mode
  settings = Settings(tui_theme='auto')
  resolved = resolve_theme(settings)
  assert resolved is not None, 'Auto theme resolution failed'
  print(f'Auto resolved theme: {resolved.id}')

  print('Loader tests passed')
  "
  # Assert: Output shows 6 available themes and resolved theme
  ```

  **Evidence to Capture**:
  - [ ] Python script output (themes list, resolved theme)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 5, 6)
  - Message: `feat(theme): add theme loader with auto-detection`
  - Files: `src/opencode_python/theme/loader.py`

---

- [ ] 5. Extend settings with theme fields

  **What to do**:
  - Extend `src/opencode_python/core/settings.py` Settings class
  - Add validation for `tui_theme` field (allow "auto" + 6 theme names)
  - Existing `tui_theme` field already exists - enhance its validation
  - Ensure backward compatibility (existing .env files without validation work)
  - No new fields needed (just enhance existing tui_theme)
  - Document new validation in docstring

  **Must NOT do**:
  - Don't add separate theme fields (use only tui_theme)
  - Don't create theme path fields (themes are bundled)
  - Don't break existing settings

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple field addition to existing Pydantic model
  - **Skills**: `[]`
    - No specific skills needed for settings extension

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 6)
  - **Blocks**: Task 8 (TUI app needs settings)
  - **Blocked By**: Task 4 (loader validates theme names)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/core/settings.py:Settings` - Existing settings class structure
  - `opencode_python/src/opencode_python/core/settings.py:tui_theme` - Existing field to enhance
  - `opencode_python/src/opencode_python/core/settings.py:model_config` - Pydantic SettingsConfigDict pattern

  **API/Type References** (contracts to implement against):
  - Loader API: `get_available_themes()` returns list for validation
  - Theme names: ["auto", "dracula", "gruvbox", "catppuccin", "nord", "tokyonight", "onedarkpro"]

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/` - Any existing settings tests (for patterns)

  **Documentation References** (specs and requirements):
  - Pydantic field validators: https://docs.pydantic.dev/latest/concepts/validators/ - Validation syntax

  **WHY Each Reference Matters** (explain the relevance):
  - Settings.py: Target file for modification
  - tui_theme field: Existing field to enhance with validation
  - Pydantic docs: Validator API for field validation

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_theme_settings.py
  - [ ] Test covers: tui_theme="auto" is accepted
  - [ ] Test covers: tui_theme="dracula" is accepted
  - [ ] Test covers: tui_theme="invalid" raises ValidationError
  - [ ] Test covers: backward compatibility (old .env files without theme field work)
  - [ ] pytest tests/test_theme_settings.py → PASS (4+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  from opencode_python.core.settings import Settings, get_settings

  # Test auto mode
  settings_auto = Settings(tui_theme='auto')
  print(f'Auto mode accepted: {settings_auto.tui_theme}')

  # Test explicit theme
  settings_theme = Settings(tui_theme='dracula')
  print(f'Dracula theme accepted: {settings_theme.tui_theme}')

  # Test invalid theme (should raise)
  try:
      settings_invalid = Settings(tui_theme='nonexistent')
      print('ERROR: Invalid theme accepted')
  except Exception as e:
      print(f'Invalid theme rejected: {type(e).__name__}')

  print('Settings tests passed')
  "
  # Assert: Output shows auto and dracula accepted, invalid theme rejected
  ```

  **Evidence to Capture**:
  - [ ] Python script output (validation results)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 4, 6)
  - Message: `feat(theme): extend settings with theme validation`
  - Files: `src/opencode_python/core/settings.py`

---

- [ ] 6. Create Textual CSS adapter

  **What to do**:
  - Create `src/opencode_python/theme/textual_adapter.py`
  - Implement `generate_css(theme: Theme) -> str`
  - Map 25 theme tokens to Textual CSS variables:
    - Backgrounds: `--background-base`, `--background-stronger`
    - Borders: `--border-base`
    - Text: `--text-base`, `--text-strong`, `--text-weak`
    - Primary: `--primary`
    - Success: `--success`
    - Warning: `--warning`
    - Error: `--error`
    - Syntax colors: `--syntax-string`, `--syntax-primitive`, `--syntax-property`, `--syntax-type`
    - Markdown: `--markdown-heading`, `--markdown-text`, `--markdown-code`
  - Generate valid CSS syntax (variable definitions: `--variable-name: #hex;`)
  - Handle missing tokens (use sensible defaults)

  **Must NOT do**:
  - Don't create dynamic CSS injection beyond variables
  - Don't add widget-specific styling (keep it generic)
  - Don't implement runtime CSS reloading

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple CSS string generation from theme data
  - **Skills**: `[]`
    - No specific skills needed for CSS generation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: Task 8 (TUI app needs CSS generator)
  - **Blocked By**: Task 1 (models), Task 4 (loader)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/tui/app.py:CSS` - Existing inline CSS in TUI app
  - `opencode/packages/ui/src/styles/colors.css` - CSS variable patterns (from opencode)

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/theme/models.py:Theme` - Theme model with token structure
  - Textual CSS syntax: Variable definitions with `--name: value;` format

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/` - CSS/style test patterns (if any)

  **Documentation References** (specs and requirements):
  - Textual docs: https://textual.textualize.io/guide/CSS/ - CSS variable syntax
  - Textual Theme variables: Built-in variable names for mapping

  **External References** (libraries and frameworks):
  - CSS variable syntax: W3C CSS custom properties spec

  **WHY Each Reference Matters** (explain the relevance):
  - TUI app CSS: Shows current inline CSS pattern to replace with dynamic CSS
  - models.py: Theme data structure for CSS generation
  - Textual docs: Official CSS variable syntax reference

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_textual_adapter.py
  - [ ] Test covers: generate_css() returns valid CSS
  - [ ] Test covers: CSS contains all 25 variables
  - [ ] Test covers: CSS uses correct hex codes from theme
  - [ ] Test covers: missing tokens use sensible defaults
  - [ ] pytest tests/test_textual_adapter.py → PASS (4+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  from opencode_python.theme.textual_adapter import generate_css
  from opencode_python.theme.loader import load_theme

  # Load dracula theme
  theme = load_theme('dracula')
  css = generate_css(theme)

  # Check CSS contains key variables
  assert '--primary:' in css, 'Missing --primary variable'
  assert '--background-base:' in css, 'Missing --background-base variable'
  assert '--text-base:' in css, 'Missing --text-base variable'

  print('CSS generated successfully')
  print('First 500 chars of CSS:')
  print(css[:500])
  "
  # Assert: Output shows CSS generation successful and contains variables
  ```

  **Evidence to Capture**:
  - [ ] Python script output (CSS generation)
  - [ ] CSS snippet (first 500 chars)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 5, 6)
  - Message: `feat(theme): add Textual CSS generator`
  - Files: `src/opencode_python/theme/textual_adapter.py`

---

- [ ] 7. Create Rich Theme adapter

  **What to do**:
  - Create `src/opencode_python/theme/rich_adapter.py`
  - Implement `create_rich_theme(theme: Theme) -> rich.Theme`
  - Map 25 theme tokens to Rich Theme styles:
    - Console background: `background-base`
    - Console foreground: `text-base`
    - Syntax string: `syntax-string`
    - Syntax keyword: `syntax-primitive`
    - Syntax function: `syntax-property`
    - Syntax type: `syntax-type`
    - Success: `success`
    - Warning: `warning`
    - Error: `error`
    - Code: `markdown-code`
    - Heading: `markdown-heading`
  - Use Rich Theme class with styles dict
  - Handle missing tokens (use Rich defaults)

  **Must NOT do**:
  - Don't create Rich-specific theme variants (use same colors as Textual)
  - Don't use INI file format (use Theme class directly)
  - Don't implement runtime theme reloading

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple Rich Theme object creation
  - **Skills**: `[]`
    - No specific skills needed for Rich adapter

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 8)
  - **Blocks**: Task 9 (tests need adapter)
  - **Blocked By**: Task 1 (models), Task 4 (loader)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/cli/main.py` - Existing Rich Console usage
  - `opencode_python/src/opencode_python/cli/ai_commands.py` - Rich usage for tables

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/theme/models.py:Theme` - Theme model with token structure
  - Rich Theme API: rich.theme.Theme(styles=...) - Target class

  **Test References** (testing patterns to follow):
  - Rich usage patterns in codebase (cli/*.py files)

  **Documentation References** (specs and requirements):
  - Rich docs: https://rich.readthedocs.io/en/stable/ - Theme class API
  - Rich Style: https://rich.readthedocs.io/en/stable/style.html - Style object usage

  **External References** (libraries and frameworks):
  - Rich documentation: Theme and Style classes

  **WHY Each Reference Matters** (explain the relevance):
  - cli/*.py: Show existing Rich patterns in codebase for consistency
  - models.py: Theme data structure for Rich mapping
  - Rich docs: Official API reference for Theme/Style

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_rich_adapter.py
  - [ ] Test covers: create_rich_theme() returns valid Theme object
  - [ ] Test covers: Theme styles contain key mappings
  - [ ] Test covers: Colors match theme tokens
  - [ ] Test covers: Missing tokens use Rich defaults
  - [ ] pytest tests/test_rich_adapter.py → PASS (4+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  from opencode_python.theme.rich_adapter import create_rich_theme
  from opencode_python.theme.loader import load_theme

  # Load dracula theme
  theme = load_theme('dracula')
  rich_theme = create_rich_theme(theme)

  # Check Rich Theme has styles
  assert rich_theme.styles is not None, 'Rich Theme has no styles'

  # Check key styles exist
  assert 'background' in rich_theme.styles, 'Missing background style'
  assert 'foreground' in rich_theme.styles, 'Missing foreground style'

  print('Rich Theme created successfully')
  print(f'Styles count: {len(rich_theme.styles)}')
  "
  # Assert: Output shows Rich Theme creation with styles
  ```

  **Evidence to Capture**:
  - [ ] Python script output (theme creation)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 8)
  - Message: `feat(theme): add Rich Theme adapter`
  - Files: `src/opencode_python/theme/rich_adapter.py`

---

- [ ] 8. Update TUI app to use themes

  **What to do**:
  - Update `src/opencode_python/tui/app.py`
  - Import theme loader, Textual adapter
  - Modify `on_mount()` to load and apply theme from settings
  - Replace inline CSS in OpenCodeTUI.CSS with dynamic CSS from adapter
  - Use `self.app.register_theme()` to register theme (Textual pattern)
  - Set `self.theme = theme_name` to apply theme (Textual pattern)
  - Handle theme loading errors with user notification
  - Log theme loading status

  **Must NOT do**:
  - Don't add theme switching UI/commands (no runtime hot-swap)
  - Don't add theme preview functionality
  - Don't modify existing UI components (only CSS injection)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Simple integration of theme loader into existing TUI app
  - **Skills**: `[]`
    - No specific skills needed for TUI integration

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final task)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 5 (settings), Task 6 (CSS adapter)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/src/opencode_python/tui/app.py` - TUI app class structure
  - `opencode_python/src/opencode_python/tui/app.py:on_mount()` - Mount point for initialization
  - `opencode_python/src/opencode_python/tui/app.py:CSS` - Existing inline CSS to replace

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/theme/loader.py:resolve_theme()` - Resolve theme from settings
  - `src/opencode_python/theme/textual_adapter.py:generate_css()` - Generate CSS for theme
  - `src/opencode_python/core/settings.py:get_settings()` - Get current settings
  - Textual App API: `app.register_theme()`, `app.theme` property

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/` - TUI app test patterns (if any)

  **Documentation References** (specs and requirements):
  - Textual docs: Theme registration and application patterns

  **WHY Each Reference Matters** (explain the relevance):
  - TUI app: Target file for integration
  - on_mount(): Initialization point for theme loading
  - CSS: Current inline CSS to replace with dynamic CSS
  - Textual docs: Official patterns for theme application

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_tui_theme.py
  - [ ] Test covers: TUI loads theme from settings
  - [ ] Test covers: CSS variables are applied correctly
  - [ ] Test covers: Invalid theme name shows error message
  - [ ] Test covers: Auto mode works with darkdetect
  - [ ] pytest tests/test_tui_theme.py → PASS (4+ tests, 0 failures)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  python -c "
  from textual.app import App
  from opencode_python.tui.app import OpenCodeTUI
  from opencode_python.core.settings import Settings

  # Create app with auto theme
  app = OpenCodeTUI()
  app.run(headless=True, timeout=2)

  # App should mount without errors
  print('TUI app with theme support started successfully')
  "
  # Assert: Output shows TUI app started
  ```

  **Evidence to Capture**:
  - [ ] Python script output (app startup)
  - [ ] Test execution output (pytest results)

  **Commit**: YES | NO (groups with 8)
  - Message: `feat(theme): integrate theme system into TUI app`
  - Files: `src/opencode_python/tui/app.py`

---

- [ ] 9. Write comprehensive test suite

  **What to do**:
  - Create `tests/test_theme.py` with comprehensive coverage
  - Test theme model validation (valid/invalid hex codes, required fields)
  - Test theme file loading (all 6 themes load successfully)
  - Test theme loader (get_available_themes, resolve_theme, fallback logic)
  - Test Textual CSS adapter (variable generation, CSS syntax)
  - Test Rich adapter (Theme object creation, color mapping)
  - Test settings integration (tui_theme validation, environment variables)
  - Test TUI integration (theme loading, CSS application)
  - Test edge cases: invalid theme names, missing theme files, darkdetect returns None
  - Achieve 90%+ code coverage for theme-related modules

  **Must NOT do**:
  - Don't test runtime theme switching (not in scope)
  - Don't test custom theme files (not supported)
  - Don't test accessibility features (not in scope)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `unspecified-low`
    - Reason: Comprehensive test suite implementation
  - **Skills**: `[]`
    - No specific skills needed for test writing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final task)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 4 (loader), Task 6 (CSS), Task 7 (Rich), Task 8 (TUI)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `opencode_python/tests/test_export_import.py` - Existing test patterns
  - `opencode_python/tests/test_export_import.py` - Test structure and fixtures

  **API/Type References** (contracts to implement against):
  - All implemented modules: models, loader, adapters, settings, TUI
  - Pydantic ValidationError: Exception type for validation tests

  **Test References** (testing patterns to follow):
  - `opencode_python/tests/test_export_import.py` - pytest usage patterns
  - pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html - Fixture patterns

  **Documentation References** (specs and requirements):
  - pytest docs: https://docs.pytest.org/en/stable/ - Testing patterns
  - Coverage reporting: pytest-cov for 90%+ goal

  **WHY Each Reference Matters** (explain the relevance):
  - test_export_import.py: Show existing test patterns for consistency
  - All modules: Target modules for comprehensive testing
  - Pydantic ValidationError: Expected exception type for validation tests

  **Acceptance Criteria** (Agent-Executable Verification):

  **If Tests Enabled**:
  - [ ] Test file created: tests/test_theme.py with 30+ tests
  - [ ] Test covers: model validation (hex codes, required fields)
  - [ ] Test covers: theme file loading (all 6 themes)
  - [ ] Test covers: loader functionality (resolve_theme, get_available_themes)
  - [ ] Test covers: CSS adapter (variable generation)
  - [ ] Test covers: Rich adapter (Theme creation)
  - [ ] Test covers: settings integration (validation, environment variables)
  - [ ] Test covers: TUI integration (theme loading)
  - [ ] Test covers: edge cases (invalid themes, missing files, darkdetect None)
  - [ ] pytest tests/test_theme.py --cov=opencode_python.theme --cov-report=term → PASS (30+ tests, 0 failures, 90%+ coverage)

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  pytest tests/test_theme.py --cov=opencode_python.theme --cov-report=term-missing
  # Assert: Tests pass with 90%+ coverage
  ```

  **Evidence to Capture**:
  - [ ] Full pytest output (test results)
  - [ ] Coverage report (90%+ coverage achieved)
  - [ ] Test counts (30+ tests passing)

  **Commit**: YES | NO (groups with 8, 9)
  - Message: `test(theme): add comprehensive theme test suite`
  - Files: `tests/test_theme.py`

---

- [ ] 10. Create documentation

  **What to do**:
  - Create `THEME.md` in project root
  - Document theme system architecture (models, loader, adapters)
  - Document configuration options (tui_theme settings, environment variables)
  - List available themes (dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro)
  - Document auto-detection behavior (darkdetect usage, fallback)
  - Provide examples of how to configure themes
  - Document minimum token list (what colors are supported)
  - Document scope exclusions (what's not supported)

  **Must NOT do**:
  - Don't document features not implemented (runtime switching, custom themes)
  - Don't add extensive widget styling examples (keep it generic)

  **Recommended Agent Profile**:
  > Select category + skills based on task domain.
  - **Category**: `writing`
    - Reason: Documentation writing requires clear explanation and examples
  - **Skills**: `[]`
    - No specific skills needed for documentation

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 9 in Wave 3)
  - **Parallel Group**: Wave 3 (with Task 9)
  - **Blocks**: None (final task)
  - **Blocked By**: None (documentation after implementation)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `README.md` - Existing documentation format and style
  - Any existing .md files in opencode_python - Documentation patterns

  **API/Type References** (contracts to document):
  - All implemented modules and their APIs
  - Settings field names and values
  - Available theme names

  **Test References** (testing patterns to follow):
  - None (documentation doesn't require tests)

  **Documentation References** (specs and requirements):
  - Pydantic docs: Settings model documentation
  - Textual docs: Theme system documentation
  - Rich docs: Theme documentation

  **External References** (libraries and frameworks):
  - Markdown syntax: https://www.markdownguide.org/ - Formatting

  **WHY Each Reference Matters** (explain the relevance):
  - README.md: Documentation style guide for consistency
  - All modules: Document complete API and usage
  - Markdown spec: Proper formatting for documentation

  **Acceptance Criteria** (Agent-Executable Verification):

  **Automated Verification (ALWAYS include)**:
  ```bash
  # Agent runs:
  cd opencode_python
  ls -la THEME.md
  # Assert: File exists and is readable
  cat THEME.md | head -50
  # Assert: Output shows theme documentation content
  ```

  **Evidence to Capture**:
  - [ ] File listing output (file exists)
  - [ ] Documentation preview (first 50 lines)

  **Commit**: YES | NO (groups with 9, 10)
  - Message: `docs(theme): add theme system documentation`
  - Files: `THEME.md`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(theme): add Pydantic theme models` | `src/opencode_python/theme/models.py` | pytest tests/test_theme_models.py |
| 2 | `feat(theme): port 6 themes from opencode` | `src/opencode_python/theme/themes/*.json` | pytest tests/test_theme_files.py |
| 3 | `chore(deps): add darkdetect for system theme detection` | `pyproject.toml` | `python -c "import darkdetect"` |
| 4 | `feat(theme): add theme loader with auto-detection` | `src/opencode_python/theme/loader.py` | pytest tests/test_theme_loader.py |
| 5 | `feat(theme): extend settings with theme validation` | `src/opencode_python/core/settings.py` | pytest tests/test_theme_settings.py |
| 6 | `feat(theme): add Textual CSS generator` | `src/opencode_python/theme/textual_adapter.py` | pytest tests/test_textual_adapter.py |
| 7 | `feat(theme): add Rich Theme adapter` | `src/opencode_python/theme/rich_adapter.py` | pytest tests/test_rich_adapter.py |
| 8 | `feat(theme): integrate theme system into TUI app` | `src/opencode_python/tui/app.py` | pytest tests/test_tui_theme.py |
| 9 | `test(theme): add comprehensive theme test suite` | `tests/test_theme.py` | pytest --cov=opencode_python.theme |
| 10 | `docs(theme): add theme system documentation` | `THEME.md` | `ls THEME.md` |

---

## Success Criteria

### Verification Commands

```bash
# Verify all tests pass with coverage
cd opencode_python
pytest tests/test_theme.py -v --cov=opencode_python.theme --cov-report=term-missing
# Expected: 30+ tests passed, 90%+ coverage

# Verify theme loading works
python -c "
from opencode_python.theme.loader import get_available_themes
themes = get_available_themes()
print(f'Available themes: {themes}')
print(f'Total: {len(themes)}')
"
# Expected: ['dracula', 'gruvbox', 'catppuccin', 'nord', 'tokyonight', 'onedarkpro']

# Verify TUI app starts with theme
python -c "
from textual.app import App
from opencode_python.tui.app import OpenCodeTUI
app = OpenCodeTUI()
print('TUI app initialized')
"
# Expected: No errors, TUI app starts successfully

# Verify settings validation works
python -c "
from opencode_python.core.settings import Settings
try:
    settings = Settings(tui_theme='invalid')
    print('ERROR: Invalid theme accepted')
except Exception as e:
    print(f'Invalid theme rejected: {type(e).__name__}')
"
# Expected: "Invalid theme rejected: ValidationError"

# Verify darkdetect integration
python -c "
import darkdetect
mode = darkdetect.theme()
print(f'System theme: {mode}')
"
# Expected: "Dark", "Light", or "None"
```

### Final Checklist

- [ ] All 6 themes ported (dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro)
- [ ] Pydantic models validate theme structure
- [ ] Theme loader discovers and loads themes
- [ ] Textual CSS adapter generates variables
- [ ] Rich adapter creates Theme objects
- [ ] Settings extended with theme validation
- [ ] TUI app applies themes on startup
- [ ] Auto-detect system dark/light mode works
- [ ] Fallback to dracula-dark when darkdetect fails
- [ ] All tests pass (90%+ coverage)
- [ ] Documentation exists (THEME.md)
- [ ] NO scope creep (only 25 tokens per theme, no runtime switching)
- [ ] Both Textual and Rich use same theme colors
- [ ] Clear error messages for invalid configurations

---

## Minimum Token List (MAXIMUM 25 per theme)

### Seeds (9 colors - ALWAYS REQUIRED)
1. neutral
2. primary
3. success
4. warning
5. error
6. info
7. interactive
8. diffAdd
9. diffDelete

### Overrides (16 colors - MAXIMUM)
10. background-base
11. background-stronger
12. border-base
13. text-base
14. text-strong
15. text-weak
16. syntax-string
17. syntax-primitive
18. syntax-property
19. syntax-type
20. markdown-heading
21. markdown-text
22. markdown-code

**Total: 25 tokens per theme (9 seeds + 16 overrides)**

### Textual CSS Variable Mapping
- `--primary`: primary
- `--success`: success
- `--warning`: warning
- `--error`: error
- `--background-base`: background-base
- `--background-stronger`: background-stronger
- `--border-subtle-color`: border-base
- `--text-primary`: text-base
- `--text-secondary`: text-weak
- `--code-background`: background-base
- `--code`: markdown-code
- `--header-text`: markdown-heading
- `--text`: markdown-text

### Rich Theme Style Mapping
- `background`: background-base
- `foreground`: text-base
- `info.primary`: primary
- `info.keyword`: syntax-primitive
- `info.string`: syntax-string
- `info.comment`: text-weak
- `success`: success
- `warning`: warning
- `error`: error
- `repr.number`: syntax-property
- `repr.str`: syntax-string

### EXCLUDED Tokens (NOT ported - Scope Guardrails)
All other override tokens from opencode (30+ tokens) are explicitly excluded:
- background-weak, background-strong, surface-* tokens
- border-weak, border-hover, border-active, border-selected, border-disabled, border-focus
- border-strong-* tokens (all states)
- surface-diff-*, surface-raised-*, surface-inset-*, surface-float-*, surface-weak, surface-weaker tokens
- syntax-constant, syntax-info tokens
- markdown-link, markdown-link-text, markdown-block-quote, markdown-emph, markdown-strong, markdown-horizontal-rule, markdown-list-item, markdown-list-enumeration, markdown-image, markdown-image-text, markdown-code-block tokens

These 30+ tokens are NOT ported to prevent scope creep. Only the 25 essential tokens listed above are included.

---

## Scope Exclusions (Explicitly NOT Building)

This section documents features explicitly EXCLUDED from this work to prevent scope creep.

**NOT Building**:
- ❌ Runtime theme switching (themes are startup-time only, restart required)
- ❌ Custom user-defined themes (no support for user-created theme files)
- ❌ Theme editor or UI for theme selection
- ❌ Theme preview functionality
- ❌ Theme auto-generation (light → dark inversion, dark → light inversion)
- ❌ Accessibility validation (WCAG contrast ratios, color blindness support)
- ❌ Per-framework theme divergence (Rich and Textual use identical colors from single source)
- ❌ Theme variants (e.g., catppuccin-latte, catppuccin-frappe - only single catppuccin theme)
- ❌ Rich-style INI config file loading (only JSON theme files supported)
- ❌ Dynamic CSS injection beyond Textual variable system
- ❌ Widget-specific styling (keep CSS generic)
- ❌ Porting all 50+ override tokens from opencode (only minimum 25 tokens)
- ❌ border-* state variants (border-focus, border-hover, border-active, border-selected - excluded)
- ❌ surface-* tokens (surface-diff-*, surface-raised-*, surface-inset-*, surface-float-*, surface-weak, surface-weaker - excluded)
- ❌ Extended markdown tokens (markdown-link, markdown-block-quote, markdown-emph, markdown-strong, markdown-list-item, markdown-list-enumeration, markdown-image, markdown-image-text, markdown-code-block - excluded)

**Building ONLY**:
- ✅ 6 bundled themes (dracula, gruvbox, catppuccin, nord, tokyonight, onedarkpro)
- ✅ 25 essential tokens per theme (9 seeds + 16 overrides)
- ✅ Startup-time theme selection via settings
- ✅ Auto-detect system dark/light mode
- ✅ Fallback to dracula-dark when darkdetect fails
- ✅ Settings integration (environment variables + .env file)
- ✅ Textual CSS variable generation
- ✅ Rich Theme object creation
- ✅ Comprehensive test coverage (90%+)
- ✅ Documentation for configuration

Any work beyond this scope is FUTURE WORK and requires explicit planning.
