# Issues - Python SDK Phase 1

## [2025-01-30] Initial Analysis

### Bugs Identified
1. **Bug #1** (FIXED): SessionStorage constructor missing required `base_dir` parameter
   - Location: `opencode_python/src/opencode_python/sdk/client.py:53`
   - Status: Fixed by plan agent
   - Verification needed: Run tests

2. **Bug #2** (PENDING): AgentExecutor creates fake Session objects
   - Location: `opencode_python/src/opencode_python/agents/__init__.py:190-198, 232-240`
   - Impact: Session metadata lost, can't integrate with real storage
   - Fix: Accept real Session object or fetch from SessionManager

3. **Bug #3** (PENDING): ToolExecutionManager.tool_registry not exposed
   - Location: `opencode_python/src/opencode_python/agents/__init__.py:289`
   - Impact: Tool permission filtering fails
   - Fix: Pass ToolRegistry to ToolExecutionManager or expose property

### Integration Issues
- TaskTool passes wrong type to AISession (SessionStorage instead of SessionManager)
- Provider streaming doesn't emit tool-call events for Anthropic
- No system prompt field in provider API

### Missing Components
- No AgentRegistry
- No ToolPermissionFilter
- No SkillInjector
- No ContextBuilder
- No AgentRuntime
- No public context building API
