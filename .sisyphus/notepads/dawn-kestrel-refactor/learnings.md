# Learnings

## Plugin Discovery Implementation (2026-02-08)

### Entry Points Design
- Entry points provide a standard plugin discovery mechanism in Python
- Groups defined in pyproject.toml under `[project.entry-points]`
- Format: `group_name = {entry_point_name = module.path:callable}`
- Must build wheel and install to test entry_points (importlib.metadata needs installed package)

### Plugin Loading Architecture
- Use `importlib.metadata.entry_points()` for Python 3.10+
- Supports synchronous and asynchronous loading patterns
- Each plugin group (tools, providers, agents) has its own loader function
- Refactored to use generic `_load_plugins()` function to reduce code duplication

### Validation Strategy
- Plugins must export specific functions or classes
- Version checking ensures compatibility
- Capability detection validates required interfaces
- Graceful failures prevent system startup issues
- Log warnings for failed imports/loads, continue processing other plugins

### Testing Approach
- TDD workflow: RED (failing tests) → GREEN (implementation) → REFACTOR
- Test plugin discovery with mocked entry points
- Verify entry_points can be loaded after building wheel
- All 10 tests pass: tool loading, provider loading, agent loading, validation, versioning

### Code Quality
- Removed unnecessary inline comments in refactoring phase
- Kept essential docstrings for public API
- Code is self-documenting without excessive comments

## Tool Plugin Discovery Implementation (2026-02-08)

### Entry Points for Tools
- Entry points defined in pyproject.toml under `[project.entry-points."dawn_kestrel.tools"]`
- Each tool has an entry point mapping name to module:class (e.g., "bash" = "dawn_kestrel.tools.builtin:BashTool")
- Plugin discovery loads tools via `importlib.metadata.entry_points()`

### Plugin Discovery Pattern
- `load_tools()` function discovers tools from entry points
- Entry points can return classes (type) or instances
- Must instantiate classes to get tool instances
- Pattern: `isinstance(plugin, type) ? plugin() : plugin`

### Backward Compatibility Strategy
- Keep direct tool imports: `from dawn_kestrel.tools import BashTool` works
- Export tool classes from builtin.py and additional.py in __all__
- Remove hard-coded registry creation functions (create_complete_registry)
- Replace with plugin-based loading in get_all_tools()

### Test Coverage
- Created tests/tools/test_tool_plugins.py with 6 test cases
- Tests verify: plugin discovery, backward compatibility, tool attributes, idempotency
- All 20 tools discovered correctly from entry points

### Key Learnings
- Entry point names ARE tool IDs (e.g., "bash" maps to BashTool)
- Plugin discovery must handle both classes and instances flexibly
- Tests should check consistency (types, IDs), not object identity
- Direct imports must continue working for backward compatibility
## Provider Plugin Discovery Implementation (2026-02-08)

### Entry Points for Providers
- Entry points defined in pyproject.toml under `[project.entry-points."dawn_kestrel.providers"]`
- Each provider has an entry point mapping name to module:class (e.g., "anthropic" = "dawn_kestrel.providers:AnthropicProvider")
- Plugin discovery loads providers via `importlib.metadata.entry_points()`

### Provider vs Tool Loading Differences
- **Providers**: Require constructor arguments (api_key), MUST be returned as classes (factories), not instances
  - Provider classes cannot be instantiated without api_key parameter
  - Plugin discovery always returns class for providers, regardless of __init__ signature
- **Tools**: Can be instantiated without arguments, may be returned as instances or classes

### Plugin Discovery Implementation
- Modified `plugin_discovery._load_plugins()` to handle providers specially
  - For provider group, always return class (factory pattern)
  - For other groups (tools), try to instantiate if possible
  - Providers require api_key argument, so they must be called later with that argument

### Provider Loading Strategy
- `get_provider()` now uses plugin discovery via `_get_provider_factories()`
- Built-in providers loaded from entry points via `plugin_discovery.load_providers()`
- Custom providers can still be registered via `register_provider_factory()`
- Cache provider factories for performance, cleared when custom providers are registered

### Backward Compatibility
- Direct provider imports still work: `from dawn_kestrel.providers import AnthropicProvider`
- `get_provider()` function signature unchanged: `get_provider(provider_id: ProviderID, api_key: str)`
- `register_provider_factory()` still works for custom provider registration
- PROVIDER_FACTORIES dict kept for backward compatibility but static entries removed
  - Empty by default: `PROVIDER_FACTORIES: Dict[ProviderID, ProviderFactory] = {}`
  - Only used for custom providers registered at runtime

### Test Coverage
- Created tests/providers/test_provider_plugins.py with 11 test cases (all passing)
- Tests verify: plugin discovery (4 providers), provider classes, get_provider(), custom registration, backward compatibility

### Key Learnings
- ProviderID enum values use hyphens (e.g., "zai-coding-plan") but entry points use underscores (e.g., "zai_coding_plan")
- Need explicit mapping between ProviderID values and entry point names
- Provider plugins must be treated differently from tool plugins due to constructor requirements
- Entry point loading returns class objects, not instances, for provider group
