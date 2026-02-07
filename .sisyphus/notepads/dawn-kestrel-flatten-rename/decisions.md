# Architectural Decisions

## Task: Establish root project layout and move packaging to repo root

### Decision 1: Keep opencode_python/ as Compatibility Shim

**Context**: 
- Old code references `import opencode_python`
- New package is `dawn_kestrel`

**Decision**:
- Keep `opencode_python/__init__.py` as a minimal compatibility shim
- Shim redirects all imports to `dawn_kestrel`
- Issues `DeprecationWarning` to guide users to update imports

**Rationale**:
- Provides smooth migration path for existing code
- No breaking changes required immediately
- Clear warning encourages users to update

### Decision 2: Flat Project Layout

**Context**:
- Original structure: `opencode_python/src/opencode_python/`
- Target: Flat layout at repo root

**Decision**:
- Move all directories to repo root
- No `src/` prefix in directory structure

**Rationale**:
- Simpler for development and testing
- Follows common Python packaging patterns
- Easier path resolution for tools

### Decision 3: Consolidate Configuration Files at Root

**Context**:
- Configuration files were in `opencode_python/`
- Root had some config files already

**Decision**:
- Move all config files to repo root
- Merge where appropriate (e.g., `.gitignore`)

**Rationale**:
- Single source of truth for project configuration
- Standard Python project layout
- Easier for tool discovery

### Decision 4: Move Tests to tests/ at Root

**Context**:
- Tests were in `opencode_python/tests/`
- Standard practice is `tests/` at repo root

**Decision**:
- Move all tests to `tests/` at root
- Update `pyproject.toml` to use `testpaths = ["tests"]`

**Rationale**:
- Standard Python test layout
- Clear separation from source code
- Consistent with tooling expectations

### Decision 5: Move Documentation to docs/ at Root

**Context**:
- Docs were scattered in `opencode_python/` and root
- Some docs already existed in `docs/`

**Decision**:
- Consolidate all markdown docs in `docs/` at root
- Keep main `README.md` at repo root

**Rationale**:
- Central documentation location
- `README.md` at root for GitHub/GitLab rendering
- Standard project documentation layout
