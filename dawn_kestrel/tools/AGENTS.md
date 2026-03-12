# TOOLS DIRECTORY

**Generated:** 2026-02-25

## OVERVIEW

Tool system with ABC, registry, permissions, adapters. 22 tools: 6 builtin + 16 additional.

## FILES

| File | Purpose |
|------|---------|
| `framework.py` | Tool ABC, ToolContext, ToolResult |
| `registry.py` | All 22 tools, `execute(tool_name, args, ctx)` |
| `builtin.py` | Bash, Read, Write, Grep, Glob, ASTGrep |
| `additional.py` | Edit, List, Task, Batch, Lsp, WebSearch, Skill |
| `permission_filter.py` | ToolPermissionFilter |
| `adapters.py` | ToolAdapter protocol |
| `prompts/*.txt` | Loaded via `get_prompt(tool_id)` |

## TOOL ABC

```python
class Tool(ABC):
    id: str
    description: str  # = get_prompt("tool_id")
    async def execute(self, args: dict, ctx: ToolContext) -> ToolResult: ...
    def parameters(self) -> dict: ...  # Pydantic schema
```

## PYDANTIC ARGS

```python
class Args(BaseModel):
    command: str = Field(description="...")
class MyTool(Tool):
    def parameters(self) -> dict: return Args.model_json_schema()
    async def execute(self, args, ctx) -> ToolResult:
        validated = Args(**args)  # validates
```

## PERMISSION ORDER (deny wins)

1. Denylist → DENY | 2. Allowlist → ALLOW | 3. Rules (last match) | 4. Default → DENY

```python
ToolPermissionFilter(denied_tools=["write"], allowed_tools=["read"])
```

## ADAPTER PATTERN

```python
adapter = BashToolAdapter(tool)
result = await adapter.execute(ctx, command="ls")  # Returns Result[dict]
```

Types: `BashToolAdapter`, `ReadToolAdapter`, `WriteToolAdapter`, `GenericToolAdapter`

## WHERE TO ADD

| Task | File |
|------|------|
| New tool | `additional.py` |
| Permissions | `permission_filter.py` |
| Adapter | `adapters.py` |
| Prompts | `prompts/{id}.txt` |

## SPECIAL TOOLS

- **BatchTool**: Parallel via `asyncio.gather`
- **TaskTool**: Subagent delegation
- **SkillTool**: Dynamic skill loading
