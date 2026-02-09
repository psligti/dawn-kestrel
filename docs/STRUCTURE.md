# Dawn Kestrel Project Structure

This document provides a guide to the Dawn Kestrel project layout, including where different types of code live, naming conventions, and legacy compatibility.

## High-Level Layout

```
.
├── dawn_kestrel/           # Main Python package (importable)
│   ├── agents/             # Agent implementations
│   ├── cli/                # Command-line interface
│   ├── context/             # Context building and file pipeline
│   ├── core/               # Core models, settings, event bus
│   ├── interfaces/          # Interface definitions
│   ├── llm/                # LLM client implementations
│   ├── permissions/         # Permission evaluation
│   ├── scripts/             # Utility scripts
│   ├── session/            # Session management
│   ├── skills/             # Skill loading
│   ├── storage/            # Data persistence
│   ├── tools/              # Tool framework and built-ins
│   └── tui/                # Textual UI implementation
├── tests/                  # Test suite (pytest)
├── docs/                   # Documentation
│   ├── examples/           # Usage examples
│   ├── performance/        # Performance benchmarks
│   ├── reviewers/          # PR review agent documentation
│   └── ...
├── scripts/                # Development and utility scripts
├── opencode_python/        # Legacy compatibility shim (deprecated)
├── pyproject.toml          # Project configuration
├── README.md               # Main documentation
└── ...
```

## Key Directories

### `dawn_kestrel/` - Main Package

The `dawn_kestrel/` directory contains all importable Python modules. This is the canonical package name for imports.

**Import pattern:**
```python
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.agents.builtin import PLAN_AGENT
from dawn_kestrel.core.settings import Settings
```

**Subdirectories:**
- `agents/` - Agent definitions (build, plan, general, explore, review)
- `cli/` - Click-based CLI commands (`dawn-kestrel` CLI)
- `context/` - File context building, git integration
- `core/` - Core models, settings, event bus, session manager
- `interfaces/` - IO handler, progress handler, notification interfaces
- `llm/` - LLM provider implementations
- `permissions/` - Permission evaluation and rulesets
- `scripts/` - Internal utility scripts
- `session/` - Session management logic
- `skills/` - SKILL.md parsing and loading
- `storage/` - JSON storage backend
- `tools/` - Tool framework and built-in tools (bash, read, write, grep, glob)
- `tui/` - Textual TUI implementation

### `tests/` - Test Suite

All tests live in the `tests/` directory at the repository root. Tests mirror the package structure.

**Example structure:**
```
tests/
├── test_sdk.py
├── test_config.py
├── agents/
│   └── test_builtin.py
├── cli/
│   └── test_main.py
└── ...
```

**Run tests:**
```bash
pytest tests/
pytest tests/test_sdk.py -v
pytest -k "test_config"  # Run tests matching pattern
```

### `docs/` - Documentation

Documentation lives in the `docs/` directory at the repository root.

**Subdirectories:**
- `examples/` - Working code examples
- `performance/` - Performance benchmarking documentation
- `reviewers/` - PR review agent documentation
- `adrs/` - Architecture Decision Records

**Key documentation files:**
- `STRUCTURE.md` (this file) - Project structure guide
- `getting-started.md` - Installation and usage guide
- `REVIEW_TOOL.md` - Review agent CLI documentation

### `scripts/` - Development Scripts

Utility and development scripts in the `scripts/` directory at repository root.

**Examples:**
- `scripts/validate-docs.py` - Validate documentation YAML frontmatter
- `scripts/run-benchmarks.py` - Run performance benchmarks

## Naming Conventions

### Import Package Name

**Canonical name:** `dawn_kestrel`

Use this for all imports in your code:

```python
from dawn_kestrel.sdk import OpenCodeAsyncClient
from dawn_kestrel.core.settings import Settings
```

### Distribution Name (pip install)

**Canonical name:** `dawn-kestrel` (with hyphen)

Use this for pip/uv tool installation:

```bash
pip install dawn-kestrel
pip install dawn-kestrel[dev]
uv tool install dawn-kestrel
```

### CLI Command Name

**Canonical name:** `dawn-kestrel` (with hyphen)

The main CLI command is `dawn-kestrel`:

```bash
dawn-kestrel list-sessions
dawn-kestrel run "my message"
dawn-kestrel tui
```

### Logging Namespace

**Canonical namespace:** `dawn_kestrel.*`

All logging should use the `dawn_kestrel` namespace:

```python
import logging
logger = logging.getLogger(__name__)  # Automatically includes "dawn_kestrel."

# Explicitly:
logger = logging.getLogger("dawn_kestrel.my_module")
```

**Example log output:**
```
dawn_kestrel.sdk - INFO - Creating session
dawn_kestrel.core.event_bus - DEBUG - Published event: session_created
```

## Configuration

### Config Directories

**Canonical config dir:** `~/.config/dawn-kestrel/`

Example:
```bash
# Linux/macOS
~/.config/dawn-kestrel/.env

# Windows
C:\Users\<username>\AppData\Local\dawn-kestrel\.env
```

### Environment Variables

**Canonical prefix:** `DAWN_KESTREL_`

Example environment variables:
```bash
DAWN_KESTREL_API_KEY=your-api-key
DAWN_KESTREL_ZAI_API_KEY=your-zai-key
DAWN_KESTREL_PROVIDER_DEFAULT=z.ai
DAWN_KESTREL_MODEL_DEFAULT=glm-4.7
```

## Legacy Compatibility



### Legacy Config Dirs

The following config directories are deprecated but still checked for backward compatibility:

- `~/.config/opencode-python/.env` (deprecated)
- `~/.config/opencode_python/.env` (deprecated)

**Config precedence (highest to lowest):**
1. `~/.config/dawn-kestrel/.env` (canonical)
2. `~/.config/opencode-python/.env` (legacy)
3. `~/.config/opencode_python/.env` (legacy)
4. `.env` file at repository root (local override)

### Legacy Environment Variables

The following environment variables are deprecated but still work:

- `OPENCODE_PYTHON_*` → Use `DAWN_KESTREL_*` instead

**Example:**
```bash
# Deprecated (still works)
OPENCODE_PYTHON_ZAI_API_KEY=your-key

# Recommended
DAWN_KESTREL_ZAI_API_KEY=your-key
```

**Environment variable precedence:**
- `DAWN_KESTREL_*` variables take precedence over `OPENCODE_PYTHON_*` variables
- Use new variables to override legacy behavior if needed

## Where Does X Go?

| I want to... | Put it here... | Example |
|--------------|----------------|----------|
| Add a new tool | `dawn_kestrel/tools/` | `dawn_kestrel/tools/my_tool.py` |
| Add a new agent | `dawn_kestrel/agents/` | `dawn_kestrel/agents/custom_agent.py` |
| Add CLI command | `dawn_kestrel/cli/` | `dawn_kestrel/cli/commands.py` |
| Add tests | `tests/` (mirror package structure) | `tests/test_my_feature.py` |
| Add documentation | `docs/` | `docs/my_feature.md` |
| Add example code | `docs/examples/` | `docs/examples/my_example.py` |
| Add utility script | `scripts/` | `scripts/my_utility.py` |
| Add benchmark | `dawn_kestrel/benchmarks/` | `dawn_kestrel/benchmarks/my_benchmark.py` |
| Add TUI screen | `dawn_kestrel/tui/` | `dawn_kestrel/tui/screens/my_screen.py` |
| Add skill | `.orchestrator/skills/` or project directory | `project/.orchestrator/skills/my_skill.md` |
| Add reviewer | `dawn_kestrel/agents/review/agents/` | `dawn_kestrel/agents/review/agents/my_reviewer.py` |

## Summary

- **Import name:** `dawn_kestrel` (use for `from X import Y`)
- **Distribution name:** `dawn-kestrel` (use for `pip install`)
- **CLI command:** `dawn-kestrel` (use for command-line invocations)
- **Logging namespace:** `dawn_kestrel.*`
- **Config dir:** `~/.config/dawn-kestrel/`
- **Env var prefix:** `DAWN_KESTREL_`
- **Legacy support:** `opencode_python` imports and commands work with deprecation warnings
