# DAWN KESTREL TESTS

**Generated:** 2026-02-25 | **Test Files:** 177+

## CONFIG (pyproject.toml)

```
testpaths=["tests"], addopts="--cov=dawn_kestrel --cov-report=term-missing", asyncio_mode="auto"
```

## STRUCTURE

```
tests/
├── conftest.py          # Root fixtures
├── agents/ core/ delegation/ harness/ integration/ llm/
├── providers/ reliability/ review/ tools/ tui/ workflow/
└── fixtures/review_baseline/  # minimal.json, typical.json
```

## NAMING

| Element | Pattern |
|---------|---------|
| Files | `test_*.py` |
| Classes | `Test<Component>` |
| Methods | `test_<action>_<scenario>` |
| Async | `@pytest.mark.asyncio` (auto-enabled) |

## MOCKING

```python
from unittest.mock import AsyncMock, Mock, MagicMock, patch
client = AsyncMock(spec=LLMClient)
client.complete = AsyncMock(return_value=LLMResponse(...))
```

## KEY FIXTURES

| Fixture | Purpose |
|---------|---------|
| `app` | OpenCodeTUI instance |
| `tmp_path` | Isolated temp directory (pytest builtin) |
| `mock_llm_client` | AsyncMock LLMClient |
| `context_builder` | ContextBuilder instance |
| `sample_agent_config` | Agent config dict |
| `sample_context_data` | Review context dict |

## TUI TESTING (tests/tui/conftest.py)

```python
await assert_text_visible(widget, "text")    # Wait for text
await assert_widget_visible(widget)          # Wait for visibility
await assert_widget_disabled(widget)         # Wait for disabled
```

## HARNESS (tests/harness/)

```python
from dawn_kestrel.core.harness.runner import (
    AgentRunner,              # Base - override _parse_response
    ReviewAgentRunner,        # JSON parsing, review formatting
    create_review_agent_runner,
)

runner = create_review_agent_runner(llm_client=client, base_dir=path)
result = await runner.run_review(system_prompt=prompt, context_data=data)
```

## COMMANDS

```bash
uv run pytest                    # All with coverage
uv run pytest tests/core/        # Specific directory
uv run pytest -x                 # Stop on first failure
uv run pytest -k "fsm"           # Filter by name
```
