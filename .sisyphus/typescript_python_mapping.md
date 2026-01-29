# TypeScript → Python Package & Feature Mapping
# OpenCode Comprehensive Analysis

**Generated**: January 27, 2026
**Analyzed**:
- TypeScript codebase: `/Users/parkermsligting/develop/agentic_python/opencode`
- Python codebase: `/Users/parkermsligting/develop/agentic_python/python_opencode`

---

## Executive Summary

This document provides a comprehensive mapping between TypeScript packages/features and their Python equivalents, based on the OpenCode implementation in both languages. The analysis covers:

- **19 TypeScript packages** across monorepo structure
- **1 Python package** (modularized)
- Core design patterns in both implementations
- Type system mappings
- Architectural patterns

---

## 1. TypeScript → Python Package Mapping

### 1.1 Core Dependencies

| TypeScript Package | Python Equivalent | Purpose | Usage Pattern |
|------------------|-------------------|----------|---------------|
| **zod** | **pydantic** | Schema validation & runtime type checking | Both used for validation schemas, parameter validation |
| **remeda** | (built-in + custom utilities) | Functional utilities | `pipe`, `sortBy`, `mergeDeep`, `mapValues` → Python list comprehensions, operator module |
| **solid-js** | (no direct equivalent) | Reactive UI framework | Python doesn't have direct equivalent; web frameworks differ |
| **hono** | **fastapi** | Web framework | Both provide lightweight, type-safe HTTP APIs |
| **ai** (Vercel AI SDK) | (custom implementation) | LLM streaming | Python implements custom streaming with httpx |
| **@solidjs/router** | **fastapi** routing | Client-side routing | Python uses FastAPI route decorators |
| **@solid-primitives/\*** | (no direct equivalent) | SolidJS primitives | Python uses different patterns (see patterns section) |
| **@kobalte/core** | (no direct equivalent) | Headless UI components | No Python equivalent (UI paradigm different) |
| **@opentui/core** | **prompt-toolkit** | Terminal UI components | Both provide rich terminal interfaces |
| **decimal.js** | **decimal** (built-in) | Precise decimal math | Built-in Python decimal module |
| **luxon** | **pendulum** | Date/time manipulation | Both provide timezone-aware datetime operations |
| **diff** | **difflib** (built-in) | Text diffing | Python's built-in difflib module |
| **ignore** | **pathspec** | .gitignore pattern matching | Both support gitignore-style patterns |
| **fuzzysort** | (no direct equivalent) | Fuzzy string matching | Would need custom implementation or `fuzzywuzzy` |
| **marked** | **markdown** (various) | Markdown parsing | Multiple Python options: `markdown`, `mistune`, `markdown2` |
| **shiki** | **pygments** or **rich** | Syntax highlighting | Both provide code highlighting |
| **tree-sitter-bash** | (no direct equivalent) | Bash grammar parsing | No direct Python equivalent |
| **ulid** | **uuid** (built-in) | Unique IDs | Python's uuid module (different format, similar purpose) |
| **yargs** | **click** | CLI parsing | Both provide rich CLI argument parsing |
| **gray-matter** | **frontmatter** (python-frontmatter) | Frontmatter parsing | Both extract YAML/JSON from markdown |
| **partial-json** | (custom implementation) | Partial JSON streaming | Would need custom implementation |
| **strip-ansi** | **ansi** (strip-ansi or rich) | ANSI code removal | Rich or custom implementation |
| **minimatch** | **fnmatch** (built-in) | Glob pattern matching | Python's built-in fnmatch module |
| **chokidar** / **@parcel/watcher** | **watchfiles** | File watching | Both provide efficient file system watching |
| **ignore** | **pathspec** | Git ignore patterns | Pathspec library |
| **bun-pty** | **asyncio** + subprocess | Pseudo-terminal | Async subprocess in Python |
| **@modelcontextprotocol/sdk** | **custom MCP implementation** | MCP protocol | Python implements MCP protocol from scratch |
| **@ai-sdk/\*** (various providers) | **httpx** (custom) | AI provider integrations | Python uses httpx directly with custom abstractions |
| **@agentclientprotocol/sdk** | (not yet implemented) | Agent protocol | TypeScript has this, Python doesn't yet |
| **@hono/zod-validator** | **pydantic** + FastAPI | Request validation | FastAPI's pydantic integration |
| **vite** | (no direct equivalent) | Build tool | Different ecosystem (Python doesn't need) |
| **turbopack/turbo** | (no direct equivalent) | Monorepo build tool | Different build paradigm |
| **playwright** | **playwright-python** | Browser automation | Same library, Python bindings |
| **tailwindcss** | (no direct equivalent in Python) | CSS framework | Python web frameworks integrate differently |
| **open** | **webbrowser** (built-in) | Open URLs/files | Python's webbrowser module |
| **clipboardy** | **pyperclip** | Clipboard access | Pyperclip for cross-platform clipboard |

---

### 1.2 TypeScript Packages Breakdown

#### Core Package: `opencode` (packages/opencode)
**Dependencies:**
- `zod` → Python: `pydantic`
- `remeda` → Python: Built-in + custom utils
- `decimal.js` → Python: `decimal`
- `diff` → Python: `difflib`
- `ignore` → Python: `pathspec`
- `ulid` → Python: `uuid`
- `yargs` → Python: `click`
- `gray-matter` → Python: `frontmatter`
- `chokidar`/`@parcel/watcher` → Python: `watchfiles`
- `bun-pty` → Python: `asyncio` + `subprocess`

**Key Features:**
- Zod schemas for validation → Pydantic BaseModel
- Tool registry with `define()` → `define_tool()` decorator
- Agent system with permissions → Agent system with permissions
- Session management → Session management
- Message handling with discriminated unions → Pydantic unions with Literal types

#### UI Package: `@opencode-ai/app`
**Dependencies:**
- `solid-js` → No direct equivalent
- `@solidjs/router` → FastAPI routing
- `@solid-primitives/*` → No equivalents (reactive primitives)
- `luxon` → `pendulum`
- `shiki` → `pygments`/`rich`
- `marked` → `markdown` packages
- `diff` → `difflib`
- `fuzzysort` → No direct equivalent

**Key Features:**
- Context-based state management → Context managers
- React hooks pattern → No Python equivalent
- SolidJS reactivity → Different paradigm

#### Console Package: `@opencode-ai/console-app`
**Dependencies:**
- `@solidjs/start` → FastAPI + Uvicorn
- `@kobalte/core` → No equivalent
- `stripe` → `stripe` (same)
- `nitro` → FastAPI
- `solid-js` → No equivalent

#### Desktop Package: `@opencode-ai/desktop`
**Dependencies:**
- `@tauri-apps/*` → No Python equivalent (different architecture)
- `@solidjs/meta` → No equivalent
- `@solid-primitives/*` → No equivalent

#### Web Package: `@opencode-ai/web`
**Dependencies:**
- `astro` → No Python equivalent (static site generator)
- `@astrojs/*` → No equivalent
- `luxon` → `pendulum`
- `shiki` → `pygments`/`rich`
- `marked` → `markdown` packages

#### Utility Package: `@opencode-ai/util`
**Dependencies:**
- `zod` → `pydantic`
- Only validation utilities

#### Plugin Package: `@opencode-ai/plugin`
**Dependencies:**
- `zod` → `pydantic`
- Plugin system definition → Custom plugin system

---

### 1.3 Python Package Analysis

From `pyproject.toml`:

| Python Package | TypeScript Equivalent | Purpose | Notes |
|--------------|----------------------|----------|--------|
| **pydantic** | zod | Schema validation | Core type system |
| **pydantic-settings** | zod-based config | Settings management | Config from env/files |
| **pendulum** | luxon | Date/time | Timezone-aware datetime |
| **click** | yargs | CLI parsing | Rich CLI interface |
| **aiohttp** | hono/fetch | Async HTTP | Async HTTP client |
| **aiofiles** | fs/promises | Async file I/O | Async file operations |
| **fastapi** | hono | Web framework | Type-safe APIs |
| **uvicorn** | (Bun runtime) | ASGI server | FastAPI server |
| **python-dotenv** | (built-in Bun) | Environment variables | Load .env files |
| **rich** | @opentui/core | Terminal UI | Rich terminal output |
| **prompt-toolkit** | @opentui/core | TUI framework | Advanced terminal UI |
| **pyyaml** | (jsonc-parser) | YAML parsing | Parse YAML config |
| **httpx** | ai SDK + fetch | HTTP client | Modern async HTTP |
| **tenacity** | custom retry | Retry logic | Exponential backoff |
| **zipp** | (no equivalent) | Path utilities | Zipfile path handling |
| **jsonschema** | zod-to-json-schema | JSON schema | JSON schema validation |
| **pathspec** | ignore | Git ignore patterns | .gitignore matching |
| **watchfiles** | @parcel/watcher | File watching | Efficient FS watching |

---

## 2. TypeScript → Python Type System Mapping

### 2.1 Core Type Patterns

| TypeScript | Python | Example | Notes |
|------------|---------|----------|--------|
| **zod** schemas | **pydantic** BaseModel | `z.object({...})` → `class X(BaseModel)` | Both provide runtime validation |
| **interface** | **Protocol** or **ABC** | `interface X { ... }` → `class X(Protocol)` | Protocol for duck typing, ABC for inheritance |
| **type** alias | **TypeAlias** | `type X = ...` → `X = ...` | Direct equivalent |
| **union** | **Union** | `X \| Y` → `Union[X, Y]` | Direct equivalent |
| **intersection** | **TypedDict** (multi-inheritance) | `X & Y` → `class X(Y, Z)` | Limited support |
| **discriminated union** | **Literal** types | `z.discriminatedUnion("type", [...])` → `Union[TypeA, TypeB]` | Manual check in Python |
| **generic** | **TypeVar** | `function foo<T>(x: T): T` → `T = TypeVar("T")` | Direct equivalent |
| **enum** | **Enum** | `enum X { A, B }` → `class X(Enum)` | Direct equivalent |
| **readonly** | **@dataclass(frozen=True)** | `readonly X` → frozen dataclass | Immutable objects |
| **Record<K, V>** | **dict[K, V]** | `Record<string, int>` → `dict[str, int]` | Direct equivalent |
| **Partial** | **Optional** fields | `Partial<X>` → all fields `Optional` | Not built-in, requires manual |
| **Required** | **no Optional** | `Required<X>` → no `Optional` | Inverse of Optional |
| **Pick<T, K>** | **TypedDict** | `Pick<X, "a"|"b">` → define new TypedDict | Manual construction |
| **Omit<T, K>** | **TypedDict** (exclusion) | `Omit<X, "a">` | Manual construction |
| **Awaited** | No special type | `Awaited<T>` → `Awaitable[T]` | Just use the type |
| **ReturnType<T>** | No special type | `ReturnType<T>` | Use `TypeVar` with bound |

### 2.2 Advanced Type Patterns

#### TypeScript:
```typescript
// Discriminated Union
export const Message = z.discriminatedUnion("role", [
  z.object({ role: z.literal("user"), content: z.string() }),
  z.object({ role: z.literal("assistant"), content: z.string() })
])

// Generic Function
function fn<T>(x: T): T {
  return x
}

// Type Guards
function isString(x: unknown): x is string {
  return typeof x === "string"
}
```

#### Python:
```python
from typing import Literal, Union, TypeVar, Protocol, TypeGuard

# Literal-based Union (discriminated)
class UserMessage(BaseModel):
    role: Literal["user"]
    content: str

class AssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: str

Message = Union[UserMessage, AssistantMessage]

# Generic Function
T = TypeVar("T")

def fn(x: T) -> T:
    return x

# Type Guard
def is_string(x: Any) -> TypeGuard[str]:
    return isinstance(x, str)
```

---

## 3. Design Patterns Mapping

### 3.1 Creational Patterns

| Pattern | TypeScript Implementation | Python Implementation |
|---------|------------------------|---------------------|
| **Factory** | `Provider.create()` methods | `create_provider()` functions |
| **Builder** | Tool.Info init pattern | Tool `define_tool()` decorator |
| **Singleton** | `Instance.state()` lazy pattern | Module-level variables, lazy init |
| **Abstract Factory** | Agent registry with `get()` | Agent registry with methods |

### 3.2 Structural Patterns

| Pattern | TypeScript | Python |
|---------|-------------|---------|
| **Adapter** | LSP adapters, MCP adapters | MCP protocol adapters |
| **Bridge** | Provider abstraction layer | Provider abstraction layer |
| **Facade** | Tool registry interface | ToolRegistry class |
| **Decorator** | `fn()` wrapper function | `define_tool()` decorator |
| **Composite** | Message parts union | Union of message parts |

### 3.3 Behavioral Patterns

| Pattern | TypeScript | Python |
|---------|-------------|---------|
| **Strategy** | Different permission strategies | Permission ruleset evaluation |
| **Observer** | Bus event system | Bus event system (eventemitter) |
| **Command** | Tool execution model | Tool execution model |
| **Chain of Responsibility** | Permission evaluation | Permission evaluation |
| **Iterator** | Async generators | Async generators |
| **Template Method** | Agent prompt templates | Agent prompt templates |
| **State** | Session status enum | Session status enum |
| **Mediator** | Bus system for events | Bus system for events |

### 3.4 Architectural Patterns

| Pattern | TypeScript | Python |
|---------|-------------|---------|
| **Repository** | Storage abstraction | Storage classes |
| **Service Layer** | Provider/Agent/Tool systems | Provider/Agent/Tool systems |
| **Event-Driven** | Bus system everywhere | Event system in Python |
| **Plugin System** | Plugin interface with hooks | Plugin interface (simpler) |
| **Dependency Injection** | `fn()` wrapper pattern | Dependency injection via init |
| **Context Pattern** | SolidJS Context API | `contextlib.contextmanager` |
| **Lazy Loading** | `lazy()` function | Lazy evaluation |

### 3.5 React/SolidJS Patterns (TypeScript) vs Python

| SolidJS Pattern | Python Equivalent |
|----------------|------------------|
| **createSignal** | No direct equivalent (reactivity is different) |
| **createStore** | State classes with updates |
| **createContext** | `contextlib.contextmanager` |
| **useContext** | Context variable access |
| **createEffect** | No direct equivalent |
| **createMemo** | `@functools.lru_cache` |
| **createResource** | Async resource loading |

---

## 4. Core Feature Mapping

### 4.1 Tool System

#### TypeScript (`packages/opencode/src/tool/tool.ts`):
```typescript
export function define<Parameters, Result>(
  id: string,
  init: Info<Parameters, Result>["init"]
): Info<Parameters, Result> {
  return {
    id,
    init: async (initCtx) => {
      const toolInfo = init instanceof Function ? await init(initCtx) : init
      // ... wrapper logic
    }
  }
}
```

#### Python (`python_opencode/src/opencode/tool/__init__.py`):
```python
def define_tool(
    tool_id: str,
    description: str,
    parameters: type[BaseModel],
    execute: Callable[[Any, ToolContext], ToolExecutionResult],
    init: Optional[Callable[[ToolInitContext], Any]] = None,
) -> ToolInfo:
    async def init_wrapper(ctx: ToolInitContext) -> dict[str, Any]:
        result = await (init or default_init)(ctx)
        return {
            "description": description,
            "parameters": parameters,
            "execute": execute,
        }
    # ...
```

### 4.2 Message Handling

#### TypeScript:
```typescript
export const Part = z.discriminatedUnion("type", [
  TextPart,
  ToolCallPart,
  FilePart,
  ImagePart,
])
```

#### Python:
```python
MessagePart = Union[TextPart, ToolCallPart, FilePart, ImagePart]
```

### 4.3 Agent System

#### TypeScript:
```typescript
export const Agent = z.object({
  name: z.string(),
  mode: z.enum(["subagent", "primary", "all"]),
  permission: PermissionNext.Ruleset,
  // ...
})
```

#### Python:
```python
class AgentInfo(BaseModel):
    name: str
    mode: AgentMode  # Enum
    permission: PermissionRuleset
```

### 4.4 Permission System

#### TypeScript:
```typescript
export const Action = z.enum(["allow", "deny", "ask"])
export const Rule = z.object({
  action: Action,
  pattern: z.string(),
})
```

#### Python:
```python
class PermissionRule(BaseModel):
    action: Literal["allow", "deny", "ask"]
    pattern: str
```

### 4.5 Event System

#### TypeScript:
```typescript
export function subscribe<Definition extends BusEvent.Definition>(
  event: Definition,
  callback: (payload: z.infer<typeof Definition>) => void
): () => void
```

#### Python:
```python
# Custom implementation (not using standard library)
class EventEmitter:
    def on(self, event: str, callback: Callable):
        # ...
```

---

## 5. Module Organization Mapping

### 5.1 TypeScript Monorepo Structure
```
opencode/
├── packages/
│   ├── opencode/          # Core CLI/Server
│   ├── app/               # SolidJS web app
│   ├── desktop/           # Tauri desktop app
│   ├── ui/               # Shared UI components
│   ├── console/app/       # Web console
│   ├── console/core/      # Console backend
│   ├── web/              # Marketing/docs site
│   ├── util/              # Shared utilities
│   ├── plugin/            # Plugin system
│   └── sdk/              # TypeScript SDK
```

### 5.2 Python Monolithic Structure
```
python_opencode/src/opencode/
├── agent/           # Agent definitions
├── bus/             # Event system
├── cli/             # CLI interface
├── command/         # Command definitions
├── config/          # Configuration
├── file/            # File operations
├── mcp/             # MCP protocol
├── models/          # Data models
├── permissions/      # Permission system
├── runtime/         # Runtime utilities
├── server/          # FastAPI server
├── session/         # Session management
├── storage/         # Storage layer
├── tool/            # Tool system
└── util/            # Utilities
```

---

## 6. Key Architectural Differences

### 6.1 Type Safety
- **TypeScript**: Compile-time + runtime (Zod)
- **Python**: Type hints + runtime (Pydantic)

### 6.2 Asynchronous Programming
- **TypeScript**: Promises, async/await, `for await`
- **Python**: asyncio, coroutines, `async for`

### 6.3 Error Handling
- **TypeScript**: `throw new Error()`, `try/catch`
- **Python**: `raise Exception()`, `try/except`

### 6.4 Module System
- **TypeScript**: ES modules (`import`/`export`)
- **Python**: Package-based (`from ... import`)

### 6.5 Decorators
- **TypeScript**: Experimental decorators, mostly for classes
- **Python**: Rich decorator ecosystem (`@dataclass`, `@property`, context managers)

### 6.6 Immutability
- **TypeScript**: `as const`, `readonly`
- **Python**: `@dataclass(frozen=True)`, `NamedTuple`

---

## 7. Missing Python Features

The following TypeScript features are **not yet implemented** in Python:

1. **Agent Client Protocol (ACP)** - TypeScript has this, Python doesn't
2. **OpenAI Responses API** - TypeScript implementation exists, Python doesn't
3. **SolidJS-based UI** - No equivalent needed (different paradigm)
4. **Desktop app (Tauri)** - No desktop app yet
5. **Marketing website** - TypeScript has Astro-based site
6. **VSCode integration** - TypeScript has VSCode extension, Python doesn't

---

## 8. Recommendations for Python Implementation

### 8.1 High Priority
1. **Implement ACP (Agent Client Protocol)** - Match TypeScript feature parity
2. **Add more design patterns** - Implement Factory, Builder patterns explicitly
3. **Enhance type safety** - Use Protocol more extensively
4. **Add comprehensive tests** - Match TypeScript test coverage

### 8.2 Medium Priority
1. **Web UI for Python** - Consider FastAPI + HTMX or Streamlit
2. **Desktop app** - Consider PySide6, PyQt, or Toga
3. **Better async patterns** - Use asyncio more extensively
4. **Plugin system** - Enhance to match TypeScript plugin capabilities

### 8.3 Low Priority
1. **Marketing site** - Static site generator (Pelican, Sphinx)
2. **VSCode extension** - Python-based VSCode extension
3. **Documentation** - Improve API documentation

---

## 9. Package Equivalents Summary

### Validation & Types
| Category | TypeScript | Python |
|----------|-------------|---------|
| Schema Validation | zod | pydantic |
| Runtime Types | TypeScript types | Type hints + pydantic |

### HTTP & Networking
| Category | TypeScript | Python |
|----------|-------------|---------|
| HTTP Client | fetch, ai SDK | httpx |
| Web Framework | hono | fastapi |
| Server Runtime | Bun, Node | uvicorn |

### CLI & Terminal
| Category | TypeScript | Python |
|----------|-------------|---------|
| CLI Parsing | yargs | click |
| Terminal UI | @opentui/core | prompt-toolkit, rich |
| File Watching | @parcel/watcher, chokidar | watchfiles |

### Data & Utilities
| Category | TypeScript | Python |
|----------|-------------|---------|
| Date/Time | luxon | pendulum |
| Diff | diff | difflib |
| UUIDs | ulid | uuid |
| CLI Colors | ansi codes | rich |
| Markdown | marked | markdown, mistune |
| Syntax Highlighting | shiki | pygments, rich |

### File System
| Category | TypeScript | Python |
|----------|-------------|---------|
| Async File I/O | fs/promises | aiofiles |
| Path operations | path | pathlib |
| Git ignore | ignore | pathspec |
| Glob patterns | minimatch | fnmatch |

### Async & Concurrency
| Category | TypeScript | Python |
|----------|-------------|---------|
| Async | Promises, async/await | asyncio |
| Retry | Custom | tenacity |
| Pseudo-terminal | bun-pty | asyncio subprocess |

---

## 10. Design Patterns - Deep Dive

### 10.1 Singleton Pattern

**TypeScript:**
```typescript
export const state = Instance.state(async () => {
  const cfg = await Config.get()
  return cfg
})
```

**Python:**
```python
# Module-level singleton
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        _instance = Config()
    return _instance
```

### 10.2 Factory Pattern

**TypeScript:**
```typescript
export function createProvider(settings: ProviderSettings) {
  switch (settings.type) {
    case "openai": return createOpenAI(settings)
    case "anthropic": return createAnthropic(settings)
  }
}
```

**Python:**
```python
def create_provider(settings: ProviderSettings) -> Provider:
    if settings.type == "openai":
        return OpenAIProvider(settings)
    elif settings.type == "anthropic":
        return AnthropicProvider(settings)
```

### 10.3 Observer Pattern (Event System)

**TypeScript:**
```typescript
export function subscribe<Definition extends BusEvent.Definition>(
  event: Definition,
  callback: (payload: z.infer<typeof Definition>) => void
): () => void {
  Bus.on(event, callback)
  return () => Bus.off(event, callback)
}
```

**Python:**
```python
class EventEmitter:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {}

    def on(self, event: str, callback: Callable):
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def emit(self, event: str, *args, **kwargs):
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(*args, **kwargs)
```

### 10.4 Strategy Pattern (Permissions)

**TypeScript:**
```typescript
export function evaluate(permission: string, pattern: string): Action {
  if (pattern === "*") return "allow"
  if (pattern.startsWith("!")) return "deny"
  return "ask"
}
```

**Python:**
```python
def evaluate_permission(permission: str, pattern: str) -> Action:
    if pattern == "*":
        return "allow"
    if pattern.startswith("!"):
        return "deny"
    return "ask"
```

### 10.5 Decorator Pattern

**TypeScript:**
```typescript
export const fn = <Schema extends z.ZodType>(
  schema: Schema,
  handler: (input: z.infer<Schema>) => Promise<any>
) => {
  // Wrap function with validation
}
```

**Python:**
```python
from functools import wraps

def validated(schema: type[BaseModel]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Validate against schema
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 11. Performance Considerations

### TypeScript
- **Runtime**: Bun (very fast)
- **Compilation**: Native TypeScript compilation
- **Bundle Size**: Tree-shaking reduces bundle size
- **Memory**: SolidJS reactivity is memory-efficient

### Python
- **Runtime**: CPython (slower than V8)
- **No compilation**: Interpreted (can use mypy for type checking)
- **Package size**: No bundling, full dependencies
- **Memory**: Pydantic adds runtime overhead

---

## 12. Testing Strategy

### TypeScript
- **Framework**: Bun test, Playwright for e2e
- **Type checking**: tsc --noEmit
- **Coverage**: bun test --coverage

### Python
- **Framework**: pytest, pytest-asyncio
- **Type checking**: mypy
- **Coverage**: pytest-cov
- **Formatting**: black, ruff

---

## 13. Future Recommendations

### For Python Port
1. **Add TypeVar constraints** - Better generic typing
2. **Use Protocol more** - Duck typing over inheritance
3. **Add mypy strict mode** - Catch more type errors
4. **Implement caching** - functools.lru_cache
5. **Add async generators** - For streaming responses
6. **Use dataclasses** - For simple data structures
7. **Add context managers** - `@contextmanager` for resource management

### For TypeScript (reference)
1. **More Protocol usage** - Better pattern matching
2. **Enhanced error types** - Discriminated unions for errors
3. **Better async patterns** - AsyncLocalStorage usage
4. **Performance optimization** - Memoization strategies

---

## 14. Glossary

- **Zod**: TypeScript-first schema validation library
- **Pydantic**: Python data validation library
- **SolidJS**: Reactive JavaScript UI framework
- **FastAPI**: Modern Python web framework
- **Remeda**: Functional utility library for TypeScript
- **Playwright**: Browser automation framework
- **Bun**: JavaScript runtime and toolkit
- **Hono**: Fast web framework for edge
- **Uvicorn**: ASGI web server for Python
- **MCP**: Model Context Protocol
- **ACP**: Agent Client Protocol
- **Type Guard**: TypeScript runtime type check
- **TypeGuard**: Python type guard for isinstance
- **Context Manager**: Python resource management pattern
- **Discriminated Union**: Union with a common discriminator property

---

**Document Version**: 1.0
**Last Updated**: January 27, 2026
**Analysis Depth**: Comprehensive (full codebase scan)
