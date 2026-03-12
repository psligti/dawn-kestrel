# DAWN KESTREL KNOWLEDGE BASE

**Generated:** 2026-03-11
**Commit:** HEAD
**Branch:** main

---

## OVERVIEW

Async/sync AI client SDK with CLI and TUI interfaces. Multi-agent orchestration with FSM-based workflows, delegation engine, and reliability patterns (rate limiting, circuit breaker, retry).

---

## COMMANDS

### Development
```bash
uv sync                           # Install dependencies
uv run pytest                     # Run all tests with coverage
uv run pytest tests/core/         # Run tests in specific directory
uv run pytest tests/core/test_fsm.py -v          # Run single test file (verbose)
uv run pytest -k "fsm"            # Run tests matching pattern
uv run pytest -x                  # Stop on first failure
uv run pytest --no-cov            # Run without coverage (faster)
uv run ruff check .               # Lint
uv run ruff check . --fix         # Lint with auto-fix
uv run mypy dawn_kestrel          # Type check (strict)
```

### CLI
```bash
dawn-kestrel --help               # CLI help
dawn-kestrel connect              # Connect to provider
dawn-kestrel run "prompt"         # Run agent
```

### Build
```bash
uv build                          # Build package (creates .whl and .tar.gz in dist/)
uv pip install -U dist/*.whl      # Install built wheel
```

---

## STRUCTURE

```
dawn-kestrel/
├── dawn_kestrel/           # Main package (flat layout, NOT src/)
│   ├── core/               # FSM, EventBus, DI, Result types
│   ├── agents/             # Agent management, Bolt Merlin subagents
│   ├── llm/                # Provider abstraction, reliability patterns
│   ├── delegation/         # Multi-agent task delegation engine
│   ├── tools/              # Tool definitions, registry, permissions
│   ├── tui/                # Textual-based TUI (screens, widgets, dialogs)
│   ├── providers/          # Provider adapters (OpenAI, Anthropic, Z.AI)
│   ├── cli/                # Click-based CLI commands
│   └── reliability/        # Queue/worker infrastructure
├── tests/                  # 177 test files, pytest with asyncio auto
├── .claude/napkin.md       # Project learnings and corrections
├── pyproject.toml          # UV build, ruff, mypy strict
└── docs/                   # Documentation and examples
```

---

## CODE STYLE

### Imports
```python
# 1. Future annotations (always first)
from __future__ import annotations

# 2. Standard library (alphabetical)
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

# 3. Third-party (alphabetical)
from pydantic import BaseModel, Field

# 4. Local imports (alphabetical, grouped by module)
from dawn_kestrel.core.result import Err, Ok, Result
```

### Type Hints
- Python 3.11+ required - use `str | None` union syntax (NOT `Optional[str]` in new code)
- All functions must have complete type annotations
- Use `TYPE_CHECKING` for circular import avoidance

### Naming
| Element | Convention | Example |
|---------|------------|--------|
| Classes | PascalCase | `AgentBuilder`, `FSMContext` |
| Functions | snake_case | `with_name`, `transition_to` |
| Variables | snake_case | `session_id`, `tool_result` |
| Constants | UPPER_SNAKE | `ALLOWED_SHELL_COMMANDS` |
| Private | Leading underscore | `_value`, `_execute_internal` |

### Error Handling (Result Pattern)
```python
from dawn_kestrel.core.result import Ok, Err, Result

async def operation() -> Result[Data]:
    if success:
        return Ok(data)
    return Err("message", code="CODE", retryable=True)

# Usage - NEVER raise, always return Result
result = await operation()
if result.is_ok():
    data = result.unwrap()
else:
    error = result.error  # Access error attribute
```

### Async Patterns
```python
# All I/O is async
async def fetch_data() -> Result[Data]:
    ...

# Type alias for hooks
type HookCallable = Callable[[FSMContext], Result[None] | Awaitable[Result[None]]]
```

### Pydantic Models
```python
from pydantic import BaseModel, Field

class BashToolArgs(BaseModel):
    command: str = Field(description="Command to execute")
    workdir: str | None = Field(default=None, description="Working directory")
```

### Protocols
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FSM(Protocol):
    async def get_state(self) -> str: ...
    async def transition_to(self, new_state: str) -> Result[None]: ...
```

---

## TESTING

### Configuration (pyproject.toml)
```
testpaths=["tests"], addopts="--cov=dawn_kestrel --cov-report=term-missing", asyncio_mode="auto"
```

### Naming
| Element | Pattern |
|---------|--------|
| Files | `test_*.py` |
| Classes | `Test<Component>` |
| Functions | `test_<action>_<scenario>` |

### Fixtures & Mocking
```python
from unittest.mock import AsyncMock, Mock, patch
import pytest

@pytest.fixture
def mock_client():
    client = AsyncMock(spec=LLMClient)
    client.complete = AsyncMock(return_value=LLMResponse(...))
    return client

@pytest.fixture
def temp_path(tmp_path):  # tmp_path is pytest builtin
    return tmp_path / "test_dir"
```

---

## KEY PATTERNS

### Agent Builder
```python
from dawn_kestrel.agents.agent_config import AgentBuilder

config = (AgentBuilder()
    .with_name("agent_name")
    .with_mode("primary")
    .with_permission([{"permission": "*", "action": "allow"}])
    .with_prompt(PROMPT)
    .with_default_fsms()
    .build()
    .unwrap())
```

### FSM Builder
```python
from dawn_kestrel.core.fsm import FSMBuilder

fsm = (FSMBuilder()
    .with_initial_state("idle")
    .with_state("running")
    .with_transition("idle", "running", "start")
    .with_entry_hook("running", on_enter)
    .with_guard("start", guard_fn)
    .build()
    .unwrap())
```

### Tool Definition
```python
from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult
from pydantic import BaseModel, Field

class MyToolArgs(BaseModel):
    path: str = Field(description="Path to process")

class MyTool(Tool):
    id = "my_tool"
    description = "Process a path"
    
    def parameters(self) -> dict[str, Any]:
        return MyToolArgs.model_json_schema()
    
    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        validated = MyToolArgs(**args)
        # ... implementation
        return ToolResult(output=result, title="Success")
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new agent | `dawn_kestrel/agents/bolt_merlin/` | Use AgentBuilder pattern |
| Add new tool | `dawn_kestrel/tools/additional.py` | Inherit from Tool ABC |
| Add provider | `dawn_kestrel/providers/` | Implement ProviderAdapter |
| FSM workflow | `dawn_kestrel/core/fsm.py` | FSMBuilder pattern |
| Test patterns | `tests/conftest.py` | pytest-asyncio, fixtures |
| TUI screens | `dawn_kestrel/tui/screens/` | Textual screens |
| CLI commands | `dawn_kestrel/cli/main.py` | Click group |
| Reliability | `dawn_kestrel/llm/rate_limiter.py`, `circuit_breaker.py` | |

---

## NOTE-LARK SKILLS (Knowledge Management)

Use note-lark MCP tools for persistent knowledge across sessions:

### Global Concerns (any project)
- **docs**: General documentation patterns
- **glossary**: Domain terminology definitions
- **learnings**: Cross-project lessons and corrections
- **principles**: Engineering principles and best practices
- **reference**: API references, cheat sheets
- **skills**: Skill definitions and usage patterns
- **specs**: Technical specifications
- **standards**: Coding standards and conventions
- **tickets**: Issue tracking templates

### Project-Specific (dawn-kestrel)
```python
# Create project-specific note
note_lark_notes_create(payload={
    "title": "DK: FSM Security Patterns",
    "content": "...",
    "tags": ["dawn-kestrel", "fsm", "security"]
})

# Search project knowledge
note_lark_memory_search(query="dawn-kestrel result pattern")
```

### Workflow
1. **Before starting**: Search memory for relevant patterns
2. **During work**: Append learnings with `memory_append`
3. **After completion**: Create structured notes for significant findings
4. **On mistakes**: Log corrections to prevent recurrence

---

## ANTI-PATTERNS

- **NEVER** use `# type: ignore` to suppress type errors
- **NEVER** use empty catch blocks `except: pass`
- **NEVER** leave code in broken state after failures
- **NEVER** commit without explicit request
- **NEVER** return `None` for errors - use `Err`
- **NEVER** use `shell=True` with user input
- **NEVER** bypass repository for storage access
- **AVOID** exception-based control flow - use Result types

---

## NOTES

- **Flat layout**: Package at root, not in `src/` (valid but non-standard)
- **UV build**: Uses uv_build backend (not setuptools)
- **Entry points**: Defined in pyproject.toml for tools, providers, agents
- **Global singletons**: `dawn_kestrel.core.event_bus.bus`, `dawn_kestrel.core.di_container.container`
- **Napkin file**: `.claude/napkin.md` tracks project-specific learnings and corrections
