# Decisions

## Plugin Discovery Implementation (2026-02-08)

### Entry Points Groups
- `dawn_kestrel.tools`: For tool plugins
- `dawn_kestrel.providers`: For provider plugins
- `dawn_kestrel.agents`: For agent plugins

### Validation Strategy
- Plugins must provide callable that returns plugin object
- Optional version metadata for compatibility checks
- Graceful degradation on load failure (log warning, continue)

### Testing Strategy
- Use pytest with mocked entry points for unit tests
- Build wheel and verify entry_points with importlib.metadata
- Test both valid and invalid plugin scenarios
