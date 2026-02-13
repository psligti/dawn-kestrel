# GitHub Copilot Provider Implementation

## TL;DR

> **Quick Summary**: Create a GitHub Copilot provider supporting full OAuth authentication flow with multi-account support (personal/work) using https://api.githubcopilot.com API endpoint with claude-haiku as default model.
>
> **Deliverables**:
> - GitHubCopilotProvider class implementing provider interface
> - OAuth authentication module with token persistence
> - Multi-account configuration support via Settings/AccountConfig
> - Account switching utility methods
> - Plugin registration in entry points
> - Comprehensive tests
> - Updated documentation (.env.example)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Git worktree setup → Phase 1 Provider → Phase 2 OAuth → Tests → Merge

---

## Context

### Original Request
Create a provider for GitHub Copilot with the ability to connect to two different accounts (personal and work). Should include helper methods for account switching and use https://github.com/anomalyco/opencode as implementation guide.

### Interview Summary

**Key Discussions**:
- Authentication: Full OAuth flow (authorization code flow) required - not static API keys
- Connections: Two accounts - Personal GitHub and Work GitHub (user-configurable names)
- Endpoint: Standard https://api.githubcopilot.com
- Default model: claude-haiku
- Helper methods: Account switching utilities (get/set current account)
- Implementation guide: Use anomalyco/opencode patterns

**Research Findings**:
- ProviderID.GITHUB_COPILOT already exists in base.py
- Multi-account configuration system exists (AccountConfig with SecretStr, Settings with nested env vars)
- Plugin system uses entry points in pyproject.toml with fallback in plugin_discovery.py
- Existing providers follow consistent interface pattern: __init__(api_key), get_models(), stream(), count_tokens(), calculate_cost()
- Test infrastructure: pytest + pytest-asyncio already configured

**Metis Review Insights**:
- No existing OAuth patterns in codebase (only static API keys)
- Recommended: Two-phase approach - implement basic provider first, then OAuth
- Recommended: Use authlib library rather than implementing OAuth from scratch
- Must NOT: Build CLI commands for account management (out of scope)
- Must NOT: Create new configuration persistence mechanism (reuse Settings)

### Metis Review

**Identified Gaps (addressed in plan)**:
- OAuth user experience: Using manual code entry flow (simpler than local server)
- Token persistence: Using existing .env and Settings mechanism
- OAuth library: Using authlib for security and reliability
- GitHub Copilot API specifics: Assuming standard patterns, marked for validation
- Testing strategy: Mocked OAuth responses + provider interface compliance tests
- Two-phase implementation: Separates OAuth complexity from provider logic

---

## Work Objectives

### Core Objective
Create a fully functional GitHub Copilot provider with OAuth authentication and multi-account support that integrates seamlessly with existing Dawn Kestrel provider architecture.

### Concrete Deliverables
- `dawn_kestrel/providers/github_copilot.py` - GitHubCopilotProvider class
- `dawn_kestrel/providers/oauth_github_copilot.py` - OAuth helper module (Phase 2)
- `dawn_kestrel/providers/account_switcher.py` - Account switching utilities
- `tests/providers/test_github_copilot_provider.py` - Provider tests
- `tests/providers/test_oauth_github_copilot.py` - OAuth flow tests
- `tests/providers/test_account_switching.py` - Multi-account tests
- Updated `dawn_kestrel/providers/__init__.py` - Export new provider
- Updated `dawn_kestrel/providers/base.py` - GITHUB_COPILOT already exists
- Updated `dawn_kestrel/core/plugin_discovery.py` - Fallback imports
- Updated `pyproject.toml` - Entry point registration
- Updated `.env.example` - GitHub Copilot configuration examples

### Definition of Done
- [ ] Provider implements all required methods (get_models, stream, count_tokens, calculate_cost)
- [ ] OAuth flow completes successfully (auth URL → code → token → refresh)
- [ ] Two accounts can be configured and switched between
- [ ] All tests pass with pytest
- [ ] Provider is discoverable via plugin system
- [ ] Code passes ruff linting and mypy type checking
- [ ] Changes committed in new git worktree and merged back

### Must Have
- GitHub Copilot provider implementing standard interface
- Full OAuth authentication flow (authorization, token exchange, refresh)
- Multi-account support (at least 2 accounts configurable)
- Account switching helper methods
- Token security using SecretStr
- Comprehensive test coverage

### Must NOT Have (Guardrails)
- CLI commands for account management (out of scope - user can use .env or existing tools)
- New configuration persistence mechanism (reuse existing Settings/AccountConfig)
- OAuth from scratch implementation (use authlib)
- GitHub Copilot-specific UI or tools beyond provider interface
- Changes to core settings.py architecture
- Account management database or storage (use existing env-based system)

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task, regardless of test strategy.

### Test Decision
- **Infrastructure exists**: YES (pytest, pytest-asyncio configured)
- **Automated tests**: TDD (RED-GREEN-REFACTOR)
- **Framework**: pytest with pytest-asyncio

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

Each task includes detailed scenarios using appropriate tools:
- Python code execution via Bash for basic verification
- pytest for test suite execution
- ruff/mypy for code quality checks
- git commands for worktree verification

**Scenario Template per Task:**
```yaml
Scenario: [Task Name - specific verification]
  Tool: Bash / pytest / git
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact command or action]
    2. [Next action with expected intermediate state]
    3. [Assertion with exact expected value]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Output file / exit code / test results]
```

**Anti-patterns to avoid:**
- ❌ "Verify the provider works correctly"
- ❌ "Test that OAuth authentication succeeds"
- ❌ "Ensure account switching works"

**Correct patterns:**
- ✅ `python -c "from dawn_kestrel.providers import GitHubCopilotProvider; provider = GitHubCopilotProvider('test-key'); assert provider.api_key == 'test-key'"`
- ✅ `pytest tests/providers/test_github_copilot_provider.py -v; assert $? == 0`

---

## Execution Strategy

### Git Worktree Workflow (CRITICAL)

**Implementation MUST happen in a separate git worktree:**

```bash
# 1. Create new worktree from current branch
git worktree add ../harness-agent-rework-github-copilot -b feature/github-copilot-provider

# 2. All development happens in worktree
cd ../harness-agent-rework-github-copilot

# 3. Commit changes in worktree
git add .
git commit -m "feat: add GitHub Copilot provider with OAuth support"

# 4. After all work is done, merge back to original branch
cd ../harness-agent-rework
git merge feature/github-copilot-provider

# 5. Cleanup worktree
git worktree remove ../harness-agent-rework-github-copilot
```

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Setup git worktree and Phase 1 provider (no OAuth)
├── Task 2: OAuth module research and design
└── Task 3: Account switching utility design

Wave 2 (After Wave 1):
├── Task 4: Phase 2 - Implement OAuth module
├── Task 5: Integrate OAuth with provider
├── Task 6: Plugin registration and exports
└── Task 7: Write tests

Wave 3 (After Wave 2):
├── Task 8: Phase 1 tests (verify before OAuth)
├── Task 9: Phase 2 tests (OAuth flow)
├── Task 10: Multi-account tests
└── Task 11: Documentation and examples

Wave 4 (After Wave 3):
└── Task 12: Code quality checks and merge back

Critical Path: Task 1 → Task 4 → Task 8 → Task 12
Parallel Speedup: ~40% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 4, 5, 6, 8 | 2, 3 |
| 2 | None | 4 | 1, 3 |
| 3 | None | 5, 10 | 1, 2 |
| 4 | 1, 2 | 5 | 6 |
| 5 | 1, 3, 4 | 9, 10 | 6, 7 |
| 6 | 1, 2, 4 | 7 | 5, 8 |
| 7 | 1, 2 | 11 | 5, 6, 8 |
| 8 | 1 | 9 | 9, 10, 11 |
| 9 | 5, 8 | 11 | 10, 11 |
| 10 | 5, 8 | 11 | 9, 11 |
| 11 | 7, 9, 10 | 12 | - |
| 12 | 11 | None | - |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2, 3 | task(category="unspecified-high", load_skills=[...], run_in_background=false) |
| 2 | 4, 5, 6, 7 | task(category="unspecified-high", load_skills=[...], run_in_background=false) |
| 3 | 8, 9, 10, 11 | task(category="quick", load_skills=[...], run_in_background=false) |
| 4 | 12 | task(category="quick", load_skills=[...], run_in_background=false) |

---

## TODOs

- [ ] 1. Setup Git Worktree and Phase 1 GitHub Copilot Provider

  **What to do**:
  - Create git worktree: `git worktree add ../harness-agent-rework-github-copilot -b feature/github-copilot-provider`
  - Create `dawn_kestrel/providers/github_copilot.py` with basic provider (static API key only)
  - Implement provider interface: __init__, get_models(), stream(), count_tokens(), calculate_cost()
  - Use standard https://api.githubcopilot.com as base_url
  - Default model: claude-haiku
  - NO OAuth in this phase - just static API key for testing provider logic

  **Must NOT do**:
  - Implement OAuth flow (deferred to Phase 2)
  - Build CLI commands
  - Modify core settings.py architecture

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `unspecified-high`
    - Reason: New provider implementation from scratch requires deep understanding of existing patterns, API design, and careful adherence to interfaces. This is not trivial refactoring or simple changes.
  - **Skills**: [`git-master`]
    - `git-master`: Required for git worktree operations and branch management
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser/UI testing needed
    - `frontend-ui-ux`: No UI components involved
    - `dev-browser`: No web scraping or browser automation

  **Parallelization**:
  - **Can Run In Parallel**: NO (must start first for other tasks)
  - **Parallel Group**: Sequential - Wave 1
  - **Blocks**: Tasks 4, 5, 6, 8
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/providers/__init__.py:89-241` - AnthropicProvider implementation (stream, get_models, cost calculation)
  - `dawn_kestrel/providers/openai.py:27-88` - OpenAIProvider structure (headers, streaming, model definitions)
  - `dawn_kestrel/providers/zai_base.py` - Base provider patterns for common functionality

  **API/Type References** (contracts to implement against):
  - `dawn_kestrel/providers/base.py:107` - ModelInfo dataclass structure
  - `dawn_kestrel/providers/base.py:29-44` - ModelCapabilities, ModelCost, ModelLimits dataclasses
  - `dawn_kestrel/providers/base.py:86-99` - TokenUsage and StreamEvent dataclasses

  **Test References** (testing patterns to follow):
  - `tests/providers/test_provider_plugins.py:19-90` - Provider interface compliance tests
  - `tests/providers/test_provider_plugins.py:pytest.mark.asyncio` - Async test patterns

  **Documentation References** (specs and requirements):
  - `.sisyphus/drafts/github-copilot-provider.md` - Interview notes and requirements
  - `.env.example:26-49` - Multi-account configuration examples

  **External References** (libraries and frameworks):
  - GitHub Copilot API: https://api.githubcopilot.com (endpoint to be validated during implementation)
  - authlib: https://docs.authlib.org/en/latest/ (OAuth library for Phase 2)

  **WHY Each Reference Matters** (explain the relevance):
  - `providers/__init__.py:89-241`: Shows complete working provider implementation with streaming, headers, error handling. Use as template for stream() method and event yielding.
  - `providers/base.py:107`: ModelInfo structure is strict - all fields (id, provider_id, api_url, name, family, capabilities, cost, limit, status, options, headers) must be populated correctly.
  - `test_provider_plugins.py:19-90`: Defines what "provider interface compliance" means - all methods must exist and be callable. Test must pass.

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/providers/test_github_copilot_provider_phase1.py
  - [ ] Test covers: provider initialization, get_models returns valid ModelInfo, stream yields StreamEvent
  - [ ] pytest tests/providers/test_github_copilot_provider_phase1.py -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Git worktree created successfully
    Tool: Bash (git)
    Preconditions: Current directory is git repository
    Steps:
      1. git worktree add ../harness-agent-rework-github-copilot -b feature/github-copilot-provider
      2. git worktree list
      3. Assert output contains "harness-agent-rework-github-copilot"
      4. cd ../harness-agent-rework-github-copilot
      5. git branch --show-current
      6. Assert output equals "feature/github-copilot-provider"
      7. ls dawn_kestrel/providers/github_copilot.py
      8. Assert file exists
    Expected Result: New worktree directory created with feature branch and provider file present
    Evidence: Git worktree list output shows new worktree
  ```

  ```yaml
  Scenario: Provider instantiates with API key
    Tool: Bash (python)
    Preconditions: Provider file created with GitHubCopilotProvider class
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.github_copilot import GitHubCopilotProvider
      provider = GitHubCopilotProvider('test-api-key-1234567890')
      assert provider.api_key == 'test-api-key-1234567890'
      assert provider.base_url == 'https://api.githubcopilot.com'
      assert hasattr(provider, 'get_models')
      assert hasattr(provider, 'stream')
      assert hasattr(provider, 'count_tokens')
      assert hasattr(provider, 'calculate_cost')
      print('SUCCESS: All assertions passed')
      "
      3. Assert stdout contains "SUCCESS: All assertions passed"
    Expected Result: Provider class instantiates correctly with all required methods
    Evidence: Python script output shows success
  ```

  ```yaml
  Scenario: get_models returns valid ModelInfo
    Tool: Bash (python)
    Preconditions: Provider implements get_models method
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.github_copilot import GitHubCopilotProvider
      from dawn_kestrel.providers.base import ModelInfo
      import asyncio

      async def test_models():
          provider = GitHubCopilotProvider('test-key')
          models = await provider.get_models()
          assert len(models) > 0, 'Should have at least one model'
          model = models[0]
          assert isinstance(model, ModelInfo), 'Should return ModelInfo instance'
          assert model.provider_id == 'github-copilot', 'Provider ID should match'
          assert model.api_url == 'https://api.githubcopilot.com', 'API URL should be standard'
          print(f'SUCCESS: Found {len(models)} models, first: {model.id}')
      asyncio.run(test_models())
      "
      3. Assert stdout contains "SUCCESS: Found"
    Expected Result: get_models returns list of ModelInfo with correct provider_id and api_url
    Evidence: Python script output shows model count and ID
  ```

  ```yaml
  Scenario: Stream method yields StreamEvent
    Tool: Bash (python)
    Preconditions: Provider implements stream method with mock HTTP
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.github_copilot import GitHubCopilotProvider
      from dawn_kestrel.providers.base import StreamEvent
      import asyncio

      async def test_stream():
          provider = GitHubCopilotProvider('test-key')
          model = await provider.get_models()
          events = []
          async for event in provider.stream(model[0], [{'role': 'user', 'content': 'test'}], []):
              events.append(event)
          assert len(events) > 0, 'Should yield events'
          assert all(isinstance(e, StreamEvent) for e in events), 'All should be StreamEvent'
          print(f'SUCCESS: Streamed {len(events)} events')
      asyncio.run(test_stream())
      "
      3. Assert stdout contains "SUCCESS: Streamed"
    Expected Result: Stream yields StreamEvent objects
    Evidence: Python script output shows event count
  ```

  **Evidence to Capture**:
  - [ ] Git worktree list output showing new worktree
  - [ ] Python script outputs showing provider tests passing
  - [ ] Test results from pytest runs

  **Commit**: YES
  - Message: `feat(phase1): add GitHub Copilot provider with basic interface`
  - Files: `dawn_kestrel/providers/github_copilot.py`
  - Pre-commit: `pytest tests/providers/test_github_copilot_provider_phase1.py -v`

---

- [ ] 2. OAuth Module Research and Design

  **What to do**:
  - Research GitHub Copilot OAuth endpoints (authorize, token, refresh)
  - Document OAuth flow: authorization URL → user authorization → code exchange → access_token + refresh_token
  - Decide on OAuth library: authlib (recommended by Metis)
  - Design token storage format using existing Settings mechanism
  - Document scope requirements for GitHub Copilot access

  **Must NOT do**:
  - Implement OAuth code (just design and research)
  - Create new storage mechanism (use .env pattern)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Research and documentation task - no code implementation yet
  - **Skills**: [`napkin`]
    - `napkin`: Record research findings and design decisions for reference
  - **Skills Evaluated but Omitted**:
    - All other skills not needed for research-only task

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1)
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `.sisyphus/drafts/github-copilot-provider.md` - Current understanding of OAuth requirements
  - `.env.example:26-49` - Existing multi-account configuration pattern

  **External References** (libraries and frameworks):
  - authlib documentation: https://docs.authlib.org/en/latest/client/oauth2.html
  - GitHub OAuth docs: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps

  **WHY Each Reference Matters**:
  - `.sisyphus/drafts/github-copilot-provider.md`: Contains confirmed requirements - "Full OAuth flow needed" - must be referenced to ensure design meets user expectations.
  - authlib docs: Primary library choice - need to understand API for authorization URL generation and token exchange.

  **Acceptance Criteria**:

  - [ ] OAuth design document created: `.sisyphus/drafts/oauth-design.md`
  - [ ] Design documents: endpoints, scopes, token storage format
  - [ ] Library choice documented with rationale

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: OAuth design document exists and contains all required sections
    Tool: Bash (cat)
    Preconditions: Draft directory exists
    Steps:
      1. cat .sisyphus/drafts/oauth-design.md
      2. Assert output contains "OAuth Flow Design"
      3. Assert output contains "Authorization Endpoint"
      4. Assert output contains "Token Exchange Endpoint"
      5. Assert output contains "Token Storage Format"
      6. Assert output contains "authlib"
    Expected Result: Design document is complete with all OAuth sections documented
    Evidence: Cat output shows all required sections present
  ```

  **Evidence to Capture**:
  - [ ] OAuth design document content

  **Commit**: NO (research only, no code changes)

---

- [ ] 3. Account Switching Utility Design

  **What to do**:
  - Design account switching utility module structure
  - Define helper methods: `get_account(provider_id, account_name)`, `set_active_account(account_name)`, `list_accounts(provider_id)`
  - Document how utilities integrate with existing Settings.get_account()
  - Design API for switching between personal/work accounts

  **Must NOT do**:
  - Implement CLI commands
  - Create new storage mechanisms

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Design-only task - no code implementation
  - **Skills**: [`napkin`]
    - `napkin`: Record design decisions for implementation phase

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1 and 2)
  - **Parallel Group**: Wave 1 (with Task 1, 2)
  - **Blocks**: Task 5, 10
  - **Blocked By**: None

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/settings.py:145-172` - Settings.get_account(), get_accounts_by_provider()
  - `dawn_kestrel/core/provider_settings.py:17-39` - AccountConfig structure

  **WHY Each Reference Matters**:
  - `settings.py:145-172`: Existing account retrieval methods - utilities should leverage these rather than reimplement. Show how to call Settings methods correctly.

  **Acceptance Criteria**:

  - [ ] Design document created: `.sisyphus/drafts/account-switcher-design.md`
  - [ ] Design documents: method signatures, integration with Settings, usage examples

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Account switcher design document exists
    Tool: Bash (cat)
    Preconditions: Draft directory exists
    Steps:
      1. cat .sisyphus/drafts/account-switcher-design.md
      2. Assert output contains "get_account"
      3. Assert output contains "set_active_account"
      4. Assert output contains "list_accounts"
      5. Assert output contains "Settings.get_account"
    Expected Result: Design document documents all helper methods and Settings integration
    Evidence: Cat output shows all methods referenced
  ```

  **Evidence to Capture**:
  - [ ] Account switcher design document content

  **Commit**: NO (design only, no code changes)

---

- [ ] 4. Phase 2 - Implement OAuth Module

  **What to do**:
  - Create `dawn_kestrel/providers/oauth_github_copilot.py`
  - Implement OAuth client using authlib:
    - generate_authorization_url(client_id, redirect_uri, scopes)
    - exchange_code_for_token(code) → returns access_token, refresh_token, expires_in
    - refresh_access_token(refresh_token) → returns new access_token
  - Implement token persistence: load/save tokens via Settings/AccountConfig
  - Add error handling for OAuth failures (invalid code, expired token)

  **Must NOT do**:
  - Implement OAuth from scratch (use authlib)
  - Build user-facing OAuth UI (this is backend utility only)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: OAuth implementation is security-critical and requires careful error handling, token management, and library integration.
  - **Skills**: [`napkin`]
    - `napkin`: Record OAuth implementation decisions and gotchas discovered
  - **Skills Evaluated but Omitted**:
    - All other skills not needed for OAuth module

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 2
  - **Blocks**: Task 5, 9
  - **Blocked By**: Tasks 1, 2

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/core/provider_settings.py:39-40` - SecretStr for secure token storage
  - `dawn_kestrel/core/settings.py:145-156` - Settings.get_account() pattern

  **External References** (libraries and frameworks):
  - authlib OAuth2: https://docs.authlib.org/en/latest/client/oauth2.html

  **WHY Each Reference Matters**:
  - `provider_settings.py:39-40`: SecretStr is MANDATORY for token security - OAuth tokens must be stored securely just like API keys.
  - `settings.py:145-156`: Shows how to retrieve AccountConfig - OAuth module needs to load/save tokens to specific accounts.

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] Test file created: tests/providers/test_oauth_github_copilot.py
  - [ ] Test covers: authorization URL generation, token exchange, token refresh
  - [ ] pytest tests/providers/test_oauth_github_copilot.py -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: OAuth module can be imported and instantiated
    Tool: Bash (python)
    Preconditions: OAuth module created in worktree
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.oauth_github_copilot import GitHubCopilotOAuthClient
      import inspect
      assert callable(GitHubCopilotOAuthClient), 'Should be callable class'
      methods = [m for m in dir(GitHubCopilotOAuthClient) if not m.startswith('_')]
      print(f'SUCCESS: OAuthClient has {len(methods)} methods: {methods}')
      "
      3. Assert stdout contains "SUCCESS:"
    Expected Result: OAuth client module imports successfully with required methods
    Evidence: Python script output shows method count
  ```

  ```yaml
  Scenario: Authorization URL generation works
    Tool: Bash (python)
    Preconditions: OAuth module implements generate_authorization_url
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.oauth_github_copilot import GitHubCopilotOAuthClient
      client = GitHubCopilotOAuthClient('test-client-id')
      url = client.generate_authorization_url('http://localhost/callback', ['read:org', 'user:email'])
      assert 'github.com/login/oauth' in url or 'api.githubcopilot.com' in url, 'URL should be valid OAuth URL'
      assert 'client_id' in url or 'client_id' in url.lower(), 'URL should contain client_id'
      print(f'SUCCESS: Generated auth URL: {url[:50]}...')
      "
      3. Assert stdout contains "SUCCESS:"
    Expected Result: generate_authorization_url returns valid OAuth authorization URL
    Evidence: Python script output shows URL prefix
  ```

  **Evidence to Capture**:
  - [ ] Python script outputs showing OAuth client functionality
  - [ ] Test results from pytest

  **Commit**: YES
  - Message: `feat(oauth): add GitHub Copilot OAuth client with authlib`
  - Files: `dawn_kestrel/providers/oauth_github_copilot.py`
  - Pre-commit: `pytest tests/providers/test_oauth_github_copilot.py -v`

---

- [ ] 5. Integrate OAuth with GitHub Copilot Provider

  **What to do**:
  - Modify GitHubCopilotProvider to accept OAuth tokens instead of static API keys
  - Add automatic token refresh when calling API
  - Support switching OAuth tokens between accounts
  - Update __init__ to accept account_name instead of api_key
  - Use OAuth module to get token from account configuration

  **Must NOT do**:
  - Change provider interface (must still accept api_key internally)
  - Break backward compatibility

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration requires careful coordination between provider and OAuth modules without breaking interfaces.
  - **Skills**: [`napkin`]
    - `napkin`: Record integration challenges and solutions discovered
  - **Skills Evaluated but Omitted**:
    - All other skills not needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 2
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 1, 3, 4

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `dawn_kestrel/providers/github_copilot.py` - Phase 1 provider (from Task 1)
  - `dawn_kestrel/providers/oauth_github_copilot.py` - OAuth module (from Task 4)
  - `dawn_kestrel/providers/__init__.py:89-91` - AnthropicProvider.__init__ signature

  **WHY Each Reference Matters**:
  - `github_copilot.py`: Must modify this file to add OAuth support - need to reference existing implementation to ensure changes are compatible.
  - `oauth_github_copilot.py`: Provides OAuth methods - need to integrate token refresh and token retrieval correctly.

  **Acceptance Criteria**:

  **If TDD (tests enabled):**
  - [ ] Test covers: OAuth token usage, automatic refresh on expired token
  - [ ] pytest tests/providers/test_github_copilot_provider.py -v → PASS

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Provider uses OAuth token instead of static key
    Tool: Bash (python)
    Preconditions: Provider integrated with OAuth module
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers.github_copilot import GitHubCopilotProvider
      # Simulate OAuth token
      provider = GitHubCopilotProvider('oauth-token-from-module')
      # Should still work like Phase 1
      assert hasattr(provider, 'get_models'), 'Should have get_models'
      assert hasattr(provider, 'stream'), 'Should have stream'
      print('SUCCESS: Provider accepts OAuth token')
      "
      3. Assert stdout contains "SUCCESS:"
    Expected Result: Provider accepts and uses OAuth tokens correctly
    Evidence: Python script output shows success
  ```

  **Evidence to Capture**:
  - [ ] Python script output showing OAuth token usage

  **Commit**: YES
  - Message: `feat(copilot): integrate OAuth authentication with provider`
  - Files: `dawn_kestrel/providers/github_copilot.py`
  - Pre-commit: `pytest tests/providers/test_github_copilot_provider.py -v`

---

- [ ] 6. Plugin Registration and Exports

  **What to do**:
  - Add entry point to pyproject.toml: `github_copilot = "dawn_kestrel.providers:GitHubCopilotProvider"`
  - Export GitHubCopilotProvider from dawn_kestrel/providers/__init__.py
  - Add to __all__ list in __init__.py
  - Update _get_provider_factories() name_to_id mapping
  - Update _load_providers_fallback() in plugin_discovery.py

  **Must NOT do**:
  - Modify other provider registrations
  - Change plugin system architecture

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mechanical registration following existing patterns - well-defined tasks with clear examples.
  - **Skills**: [`git-master`]
    - `git-master`: Verify entry point syntax and registration correctness

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 5)
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: Task 11
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `pyproject.toml:83-87` - Existing provider entry points
  - `dawn_kestrel/providers/__init__.py:52-56` - name_to_id mapping
  - `dawn_kestrel/providers/__init__.py:67-82` - __all__ export list
  - `dawn_kestrel/core/plugin_discovery.py:195-199` - _load_providers_fallback()

  **WHY Each Reference Matters**:
  - `pyproject.toml:83-87`: Exact syntax for entry point registration - must match this pattern exactly.
  - `providers/__init__.py:52-56`: name_to_id maps entry point names to ProviderID enum - must add "github_copilot": ProviderID.GITHUB_COPILOT.
  - `plugin_discovery.py:195-199`: Fallback imports for when entry points don't work - must add GitHubCopilotProvider here.

  **Acceptance Criteria**:

  - [ ] Entry point added to pyproject.toml under [project.entry-points."dawn_kestrel.providers"]
  - [ ] Provider exported from __init__.py __all__
  - [ ] name_to_id mapping updated

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Entry point registered in pyproject.toml
    Tool: Bash (grep)
    Preconditions: pyproject.toml modified
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. grep -A 5 '\[project.entry-points."dawn_kestrel.providers"\]' pyproject.toml
      3. Assert output contains "github_copilot"
      4. Assert output contains "dawn_kestrel.providers:GitHubCopilotProvider"
      5. cat pyproject.toml | grep -c "github_copilot ="
      6. Assert output equals "1", 'Should have exactly one github_copilot entry'
    Expected Result: Entry point for github_copilot provider is present in pyproject.toml
    Evidence: Grep output shows github_copilot entry point
  ```

  ```yaml
  Scenario: Provider exported from __init__.py
    Tool: Bash (python)
    Preconditions: __init__.py modified
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.providers import GitHubCopilotProvider
      from dawn_kestrel.providers.base import ProviderID
      print('SUCCESS: GitHubCopilotProvider exported correctly')
      "
      3. Assert stdout contains "SUCCESS:"
    Expected Result: GitHubCopilotProvider can be imported from dawn_kestrel.providers
    Evidence: Python import succeeds without errors
  ```

  ```yaml
  Scenario: Plugin discovery finds GitHub Copilot provider
    Tool: Bash (python)
    Preconditions: Entry points and fallback imports updated
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. python -c "
      from dawn_kestrel.core.plugin_discovery import load_providers
      providers = load_providers()
      assert 'github_copilot' in providers, 'Should find github_copilot provider'
      assert callable(providers['github_copilot']), 'Should be callable'
      print(f'SUCCESS: Found {len(providers)} providers, including github_copilot')
      "
      3. Assert stdout contains "SUCCESS:"
    Expected Result: Plugin discovery system detects github_copilot provider
    Evidence: Python script output shows provider found
  ```

  **Evidence to Capture**:
  - [ ] Grep output showing entry point
  - [ ] Python import output
  - [ ] Plugin discovery output

  **Commit**: YES
  - Message: `feat(plugins): register GitHub Copilot provider in entry points`
  - Files: `pyproject.toml`, `dawn_kestrel/providers/__init__.py`, `dawn_kestrel/core/plugin_discovery.py`
  - Pre-commit: `python -c "from dawn_kestrel.providers import GitHubCopilotProvider; print('OK')"`

---

- [ ] 7. Write Comprehensive Tests

  **What to do**:
  - Test Phase 1 provider (static API key): tests/providers/test_github_copilot_provider_phase1.py
  - Test OAuth module: tests/providers/test_oauth_github_copilot.py
  - Test integrated provider: tests/providers/test_github_copilot_provider.py
  - Test multi-account: tests/providers/test_multi_account_github_copilot.py
  - Test plugin discovery: tests/providers/test_github_copilot_plugin.py
  - Use pytest-asyncio for all async tests
  - Mock HTTP responses for all tests

  **Must NOT do**:
  - Write tests requiring real GitHub credentials (mock everything)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Test writing follows existing patterns - straightforward with clear examples.
  - **Skills**: [`napkin`]
    - `napkin`: Record testing patterns and edge cases covered

  **Parallelization**:
  - **Can Run In Parallel**: NO (needs provider and OAuth complete)
  - **Parallel Group**: Sequential - Wave 2
  - **Blocks**: Task 8, 9, 10, 11
  - **Blocked By**: Tasks 1, 2, 4, 5, 6

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `tests/providers/test_provider_plugins.py:19-91` - Provider interface compliance test patterns
  - `tests/providers/test_provider_plugins.py:37-63` - get_provider with plugin discovery test
  - `tests/providers/test_provider_plugins.py:@pytest.mark.asyncio` - Async test decorator usage

  **WHY Each Reference Matters**:
  - `test_provider_plugins.py:19-91`: Shows how to test required methods exist and are callable - must follow this pattern for new provider tests.

  **Acceptance Criteria**:

  - [ ] test_github_copilot_provider_phase1.py created and passes
  - [ ] test_oauth_github_copilot.py created and passes
  - [ ] test_github_copilot_provider.py created and passes
  - [ ] test_multi_account_github_copilot.py created and passes
  - [ ] test_github_copilot_plugin.py created and passes
  - [ ] All tests use pytest.mark.asyncio decorator

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: All test files exist
    Tool: Bash (ls)
    Preconditions: Tests directory exists
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. ls tests/providers/test_github_copilot*.py
      3. Assert output contains "test_github_copilot_provider_phase1.py"
      4. Assert output contains "test_oauth_github_copilot.py"
      5. Assert output contains "test_github_copilot_provider.py"
      6. Assert output contains "test_multi_account_github_copilot.py"
      7. Assert output contains "test_github_copilot_plugin.py"
    Expected Result: All required test files are present in tests/providers/
    Evidence: Ls output shows all test files
  ```

  ```yaml
  Scenario: All tests pass
    Tool: Bash (pytest)
    Preconditions: Test files created with pytest-asyncio
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. pytest tests/providers/test_github_copilot*.py -v --tb=short
      3. Assert exit code equals 0
      4. pytest tests/providers/test_github_copilot*.py -v --tb=short | grep -E "(PASSED|FAILED|ERROR)"
      5. Assert output does NOT contain "FAILED"
      6. Assert output does NOT contain "ERROR"
    Expected Result: All GitHub Copilot provider tests pass
    Evidence: Pytest output shows all tests PASSED
  ```

  **Evidence to Capture**:
  - [ ] Ls output showing test files
  - [ ] Pytest results showing all tests passed

  **Commit**: YES
  - Message: `test: add comprehensive GitHub Copilot provider tests`
  - Files: `tests/providers/test_github_copilot_provider_phase1.py`, `tests/providers/test_oauth_github_copilot.py`, `tests/providers/test_github_copilot_provider.py`, `tests/providers/test_multi_account_github_copilot.py`, `tests/providers/test_github_copilot_plugin.py`
  - Pre-commit: `pytest tests/providers/test_github_copilot*.py -v`

---

- [ ] 8. Phase 1 Tests (Verify Before OAuth)

  **What to do**:
  - Run test_github_copilot_provider_phase1.py
  - Verify all Phase 1 tests pass
  - Confirm provider works with static API key
  - Validate model definitions and streaming

  **Must NOT do**:
  - Skip OAuth tests (those come in Task 9)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification task - just run tests and check results
  - **Skills**: [`napkin`]
    - `napkin`: Record any Phase 1 failures or issues discovered

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 3
  - **Blocks**: None (verification only)
  - **Blocked By**: Task 1

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `tests/providers/test_provider_plugins.py` - Existing test running patterns

  **WHY Each Reference Matters**:
  - Existing test patterns show how to use pytest correctly - must follow these patterns.

  **Acceptance Criteria**:

  - [ ] pytest tests/providers/test_github_copilot_provider_phase1.py -v → exit code 0
  - [ ] All tests marked as PASSED

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Phase 1 tests all pass
    Tool: Bash (pytest)
    Preconditions: Worktree with Phase 1 provider and tests
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. pytest tests/providers/test_github_copilot_provider_phase1.py -v
      3. Assert exit code equals 0
      4. pytest tests/providers/test_github_copilot_provider_phase1.py -v | grep -E "(PASSED|FAILED|ERROR)" | head -20
      5. Assert output does NOT contain "FAILED"
      6. Assert output does NOT contain "ERROR"
    Expected Result: All Phase 1 tests pass without failures or errors
    Evidence: Pytest output shows only PASSED tests
  ```

  **Evidence to Capture**:
  - [ ] Pytest output showing test results

  **Commit**: NO (verification only, no code changes)

---

- [ ] 9. Phase 2 Tests (OAuth Flow)

  **What to do**:
  - Run test_oauth_github_copilot.py
  - Verify OAuth authorization URL generation
  - Verify token exchange with mocked responses
  - Verify token refresh functionality
  - Ensure error handling for invalid codes/expired tokens

  **Must NOT do**:
  - Test with real GitHub credentials (mock only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification task - run OAuth-specific tests
  - **Skills**: [`napkin`]
    - `napkin`: Record OAuth test failures or edge cases

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 3
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 4, 5

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `tests/providers/test_oauth_github_copilot.py` - OAuth test patterns (from Task 7)

  **WHY Each Reference Matters**:
  - OAuth tests must match patterns defined in Task 7 to ensure consistency.

  **Acceptance Criteria**:

  - [ ] pytest tests/providers/test_oauth_github_copilot.py -v → exit code 0
  - [ ] All OAuth flow tests pass

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: OAuth tests all pass
    Tool: Bash (pytest)
    Preconditions: Worktree with OAuth module and tests
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. pytest tests/providers/test_oauth_github_copilot.py -v
      3. Assert exit code equals 0
      4. pytest tests/providers/test_oauth_github_copilot.py -v | grep -E "(PASSED|FAILED|ERROR)"
      5. Assert output does NOT contain "FAILED"
      6. Assert output does NOT contain "ERROR"
    Expected Result: All OAuth tests pass without failures or errors
    Evidence: Pytest output shows only PASSED tests
  ```

  **Evidence to Capture**:
  - [ ] Pytest output showing OAuth test results

  **Commit**: NO (verification only, no code changes)

---

- [ ] 10. Multi-Account Tests

  **What to do**:
  - Run test_multi_account_github_copilot.py
  - Verify two accounts can be configured (personal, work)
  - Verify account switching works correctly
  - Ensure Settings integration retrieves correct accounts
  - Test helper methods: get_account, set_active_account, list_accounts

  **Must NOT do**:
  - Test account management CLI (out of scope)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification task - test multi-account functionality
  - **Skills**: [`napkin`]
    - `napkin`: Record multi-account edge cases discovered

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 3
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 3, 5

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `tests/providers/test_multi_account_github_copilot.py` - Multi-account test patterns (from Task 7)
  - `dawn_kestrel/core/settings.py:145-172` - Settings account retrieval patterns

  **WHY Each Reference Matters**:
  - Multi-account tests must verify Settings methods work correctly with GitHub Copilot accounts.

  **Acceptance Criteria**:

  - [ ] pytest tests/providers/test_multi_account_github_copilot.py -v → exit code 0
  - [ ] All multi-account tests pass

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: Multi-account tests all pass
    Tool: Bash (pytest)
    Preconditions: Worktree with multi-account tests
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. pytest tests/providers/test_multi_account_github_copilot.py -v
      3. Assert exit code equals 0
      4. pytest tests/providers/test_multi_account_github_copilot.py -v | grep -E "(PASSED|FAILED|ERROR)"
      5. Assert output does NOT contain "FAILED"
      6. Assert output does NOT contain "ERROR"
    Expected Result: All multi-account tests pass without failures or errors
    Evidence: Pytest output shows only PASSED tests
  ```

  **Evidence to Capture**:
  - [ ] Pytest output showing multi-account test results

  **Commit**: NO (verification only, no code changes)

---

- [ ] 11. Documentation and Examples

  **What to do**:
  - Update .env.example with GitHub Copilot configuration examples
  - Document two-account setup (personal, work)
  - Add comments explaining OAuth flow steps
  - Document account switching helper methods
  - Add usage examples in README or docs

  **Must NOT do**:
  - Create new documentation system (use existing files)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation task - requires clear, concise writing
  - **Skills**: [`napkin`]
    - `napkin`: Record documentation gaps found during writing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential - Wave 3
  - **Blocks**: Task 12
  - **Blocked By**: Tasks 2, 4, 9, 10

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `.env.example:26-49` - Existing multi-account configuration examples
  - `.env.example:1-15` - Comment style and formatting

  **WHY Each Reference Matters**:
  - `.env.example:26-49`: Shows exact format for multi-account configuration with nested env vars - must follow this pattern.

  **Acceptance Criteria**:

  - [ ] .env.example updated with GitHub Copilot examples
  - [ ] Two account examples provided (personal, work)
  - [ ] OAuth flow documented in comments

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: .env.example contains GitHub Copilot configuration
    Tool: Bash (grep)
    Preconditions: .env.example updated
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. grep -A 10 "GitHub Copilot" .env.example
      3. Assert output contains "DAWN_KESTREL__ACCOUNTS__PERSONAL__PROVIDER_ID=github-copilot"
      4. Assert output contains "DAWN_KESTREL__ACCOUNTS__WORK__PROVIDER_ID=github-copilot"
      5. grep -c "DAWN_KESTREL__ACCOUNTS__.*__PROVIDER_ID=github-copilot" .env.example
      6. Assert output is at least "2", 'Should have at least 2 GitHub Copilot account examples'
    Expected Result: .env.example contains GitHub Copilot configuration with personal and work accounts
    Evidence: Grep output shows both account configurations
  ```

  ```yaml
  Scenario: Documentation explains OAuth flow
    Tool: Bash (grep)
    Preconditions: .env.example updated with OAuth comments
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. grep -i "oauth" .env.example | head -5
      3. Assert output exists (OAuth comments present)
      4. grep -i "authorization" .env.example | head -3
      5. Assert output exists (Authorization step documented)
    Expected Result: .env.example contains OAuth flow documentation
    Evidence: Grep output shows OAuth-related comments
  ```

  **Evidence to Capture**:
  - [ ] Grep output showing GitHub Copilot configuration
  - [ ] Grep output showing OAuth documentation

  **Commit**: YES
  - Message: `docs: add GitHub Copilot configuration examples and OAuth flow documentation`
  - Files: `.env.example`
  - Pre-commit: `cat .env.example | grep "github-copilot" | head -5`

---

- [ ] 12. Code Quality Checks and Merge Back

  **What to do**:
  - Run ruff linting on all new files
  - Run mypy type checking on all new files
  - Fix any linting or type errors
  - Verify all tests pass one final time
  - Commit all changes in worktree
  - Switch back to main directory
  - Merge feature branch into original branch
  - Cleanup worktree: `git worktree remove ../harness-agent-rework-github-copilot`

  **Must NOT do**:
  - Push to remote (merge locally only, user can push later)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Final verification and git operations - well-defined tasks
  - **Skills**: [`git-master`]
    - `git-master`: Required for git worktree cleanup and merge operations

  **Parallelization**:
  - **Can Run In Parallel**: NO (final task)
  - **Parallel Group**: Sequential - Wave 4
  - **Blocks**: None (final task)
  - **Blocked By**: Task 11

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `typecheck.sh` - Type checking script pattern
  - Git worktree documentation: `git help worktree`

  **WHY Each Reference Matters**:
  - `typecheck.sh`: Shows how to run mypy correctly - must follow this pattern.
  - `git worktree`: Correct syntax for cleanup is critical to avoid leaving stale worktrees.

  **Acceptance Criteria**:

  - [ ] ruff check dawn_kestrel/providers/github_copilot.py → no errors
  - [ ] ruff check dawn_kestrel/providers/oauth_github_copilot.py → no errors
  - [ ] mypy dawn_kestrel/providers/github_copilot.py → no errors
  - [ ] mypy dawn_kestrel/providers/oauth_github_copilot.py → no errors
  - [ ] All tests pass: pytest tests/providers/test_github_copilot*.py -v
  - [ ] Changes committed in worktree
  - [ ] Feature branch merged back to original branch
  - [ ] Worktree cleaned up

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  ```yaml
  Scenario: All code passes ruff linting
    Tool: Bash (ruff)
    Preconditions: Worktree with all new Python files
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. ruff check dawn_kestrel/providers/github_copilot.py
      3. Assert exit code equals 0
      4. ruff check dawn_kestrel/providers/oauth_github_copilot.py
      5. Assert exit code equals 0
      6. ruff check dawn_kestrel/providers/account_switcher.py
      7. Assert exit code equals 0
    Expected Result: All new Python files pass ruff linting without errors
    Evidence: Ruff check commands all return exit code 0
  ```

  ```yaml
  Scenario: All code passes mypy type checking
    Tool: Bash (mypy)
    Preconditions: Worktree with all new Python files
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. mypy dawn_kestrel/providers/github_copilot.py
      3. Assert exit code equals 0
      4. mypy dawn_kestrel/providers/oauth_github_copilot.py
      5. Assert exit code equals 0
      6. mypy dawn_kestrel/providers/account_switcher.py
      7. Assert exit code equals 0
    Expected Result: All new Python files pass mypy type checking without errors
    Evidence: Mypy commands all return exit code 0
  ```

  ```yaml
  Scenario: All tests pass final verification
    Tool: Bash (pytest)
    Preconditions: Worktree with all tests
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. pytest tests/providers/test_github_copilot*.py -v
      3. Assert exit code equals 0
      4. pytest tests/providers/test_github_copilot*.py -v | tail -20
      5. Assert output contains "passed"
      6. Assert output does NOT contain "FAILED"
    Expected Result: All GitHub Copilot provider tests pass in final verification
    Evidence: Pytest output shows all tests passed
  ```

  ```yaml
  Scenario: Changes committed and merged back
    Tool: Bash (git)
    Preconditions: Worktree with completed implementation
    Steps:
      1. cd ../harness-agent-rework-github-copilot
      2. git add .
      3. git commit -m "feat: complete GitHub Copilot provider with OAuth and multi-account support"
      4. git log --oneline -1
      5. Assert output contains "feat: complete GitHub Copilot provider"
      6. cd ../harness-agent-rework
      7. git status
      8. Assert current branch is correct
      9. git merge feature/github-copilot-provider --no-edit
      10. Assert exit code equals 0
      11. git log --oneline | head -1
      12. Assert output contains "feat: complete GitHub Copilot provider"
      13. git worktree remove ../harness-agent-rework-github-copilot
      14. git worktree list
      15. Assert output does NOT contain "harness-agent-rework-github-copilot"
    Expected Result: Changes committed in worktree, merged back to original branch, and worktree cleaned up
    Evidence: Git commands show successful commit, merge, and cleanup
  ```

  **Evidence to Capture**:
  - [ ] Ruff check outputs (exit codes)
  - [ ] Mypy check outputs (exit codes)
  - [ ] Final pytest test results
  - [ ] Git log showing commit message
  - [ ] Git status showing merge success
  - [ ] Git worktree list showing cleanup

  **Commit**: NO (final task - merge is commit in original branch)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(phase1): add GitHub Copilot provider with basic interface` | dawn_kestrel/providers/github_copilot.py | pytest tests/providers/test_github_copilot_provider_phase1.py -v |
| 4 | `feat(oauth): add GitHub Copilot OAuth client with authlib` | dawn_kestrel/providers/oauth_github_copilot.py | pytest tests/providers/test_oauth_github_copilot.py -v |
| 5 | `feat(copilot): integrate OAuth authentication with provider` | dawn_kestrel/providers/github_copilot.py | pytest tests/providers/test_github_copilot_provider.py -v |
| 6 | `feat(plugins): register GitHub Copilot provider in entry points` | pyproject.toml, dawn_kestrel/providers/__init__.py, dawn_kestrel/core/plugin_discovery.py | python -c "from dawn_kestrel.providers import GitHubCopilotProvider; print('OK')" |
| 7 | `test: add comprehensive GitHub Copilot provider tests` | tests/providers/test_github_copilot_provider_phase1.py, tests/providers/test_oauth_github_copilot.py, tests/providers/test_github_copilot_provider.py, tests/providers/test_multi_account_github_copilot.py, tests/providers/test_github_copilot_plugin.py | pytest tests/providers/test_github_copilot*.py -v |
| 11 | `docs: add GitHub Copilot configuration examples and OAuth flow documentation` | .env.example | cat .env.example | grep "github-copilot" | head -5 |
| Final (after merge) | `merge: GitHub Copilot provider implementation` | - | pytest tests/providers/test_github_copilot*.py -v |

---

## Success Criteria

### Verification Commands
```bash
# Verify provider is discoverable
python -c "from dawn_kestrel.providers import GitHubCopilotProvider; print('OK')"

# Verify provider works with mock OAuth token
python -c "from dawn_kestrel.providers import GitHubCopilotProvider; p = GitHubCopilotProvider('test-token'); assert hasattr(p, 'get_models'); print('OK')"

# Verify plugin discovery
python -c "from dawn_kestrel.core.plugin_discovery import load_providers; assert 'github_copilot' in load_providers(); print('OK')"

# Verify all tests pass
pytest tests/providers/test_github_copilot*.py -v

# Verify code quality
ruff check dawn_kestrel/providers/github_copilot.py
mypy dawn_kestrel/providers/github_copilot.py

# Verify configuration examples exist
grep "DAWN_KESTREL__ACCOUNTS__PERSONAL__PROVIDER_ID=github-copilot" .env.example
```

### Final Checklist
- [ ] GitHub Copilot provider implements all required methods
- [ ] OAuth authentication flow works (authorization, token exchange, refresh)
- [ ] Two accounts can be configured (personal, work) with env vars
- [ ] Account switching helper methods work correctly
- [ ] All tests pass (Phase 1, OAuth, multi-account, plugin discovery)
- [ ] Provider is discoverable via plugin system
- [ ] Code passes ruff linting and mypy type checking
- [ ] Documentation updated (.env.example has configuration examples)
- [ ] Changes committed in git worktree
- [ ] Feature branch merged back to original branch
- [ ] Git worktree cleaned up
