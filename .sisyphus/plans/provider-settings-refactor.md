# Multi-Account Provider Settings System

## TL;DR

> **Quick Summary**: Implement a multi-account provider settings system using Pydantic Settings that loads credentials from multiple .env files (repo + home directory) with type-safe ProviderID enum and dict-based account lookup.
>
> **Deliverables**:
> - New `provider_settings.py` with AccountConfig Pydantic model
> - Updated `settings.py` with multi-.env file loading and accounts dict
> - Helper methods for account lookup (get_account, get_accounts_by_provider, get_default_account)
> - Removal of legacy api_keys fields (breaking change)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO - sequential (breaking change requires careful order)
> **Critical Path**: Create AccountConfig → Update Settings → Add helper methods → Test → Verify breaking change

---

## Context

### Original Request

User wants a config and settings update that will:
- Support multiple accounts with multiple providers
- Store credentials in dotenv files in BOTH: repo directory and home directory (`~/.config/opencode-python/.env`)
- Use Pydantic Settings (already installed)
- Make provider IDs an enum (reuse existing ProviderID)
- Make the list of accounts a dict in settings for easy lookup
- No need to keep adding credentials in CLI args or export variables

### Interview Summary

**Key Discussions**:
- Home directory location: `~/.config/opencode-python/.env` (XDG config directory)
- Account naming: Named accounts with string keys (e.g., `accounts['openai-prod']`, `accounts['anthropic-dev']`)
- Backward compatibility: Breaking change - remove `api_keys` and `api_keys_coding` fields
- Environment variable schema: Nested variables with `__` delimiter (e.g., `OPENCODE_PYTHON_ACCOUNTS__OPENAI_PROD__API_KEY=value`)
- Provider-specific credentials: Generic `api_key: SecretStr` only
- Validation: Lenient validation (warn only, don't reject)
- Test strategy: Tests-after (pytest)

**Research Findings**:
- Pydantic Settings already installed (pydantic>=2.12, pydantic-settings>=2.0)
- Existing Settings class uses pydantic_settings.BaseSettings
- ProviderID enum exists with comprehensive provider list (18 providers)
- pytest infrastructure available with pytest-asyncio and pytest-cov
- Existing `api_keys: Dict[str, SecretStr]` field must be removed (breaking change)

### Metis Review

**Critical gaps addressed**:
- File precedence: Pydantic loads .env files in order with later files overriding earlier ones (home directory overrides repo)
- Error handling: `get_account()` returns `None` for non-existent accounts, `get_accounts_by_provider()` returns empty dict
- Empty credentials: Accepted (lenient validation)
- Invalid provider IDs: Pydantic ValidationError raised at load time
- Account names: Case-sensitive, hyphens/underscores allowed

**Guardrails applied**:
- MUST NOT add UI or CLI commands for account management
- MUST NOT add account CRUD operations (create/update/delete API)
- MUST NOT add credential rotation or refresh mechanisms
- MUST NOT modify ProviderID enum or provider classes
- MUST NOT add comprehensive credential validation beyond type checking
- MUST NOT add custom exception types beyond Pydantic's
- MUST NOT add configuration file encryption

**Missing acceptance criteria added**:
- Multi-file loading verification (both .env files merged with precedence)
- File precedence verification (home overrides repo)
- Account lookup edge cases (non-existent returns None)
- Empty credential handling (accepted)
- Breaking change verification (old fields removed)
- SecretStr security verification (secrets not leaked in str/repr)
- ProviderID type safety (invalid provider raises ValidationError)

---

## Work Objectives

### Core Objective

Create a robust multi-account provider settings system with Pydantic Settings that:
- Loads credentials from two .env files with precedence (repo → home)
- Supports named accounts across multiple providers
- Provides type-safe account lookup using ProviderID enum
- Secures credentials with SecretStr
- Eliminates need for CLI args or export variables for credentials

### Concrete Deliverables

- `src/opencode_python/core/provider_settings.py` - New module with AccountConfig Pydantic model
- Updated `src/opencode_python/core/settings.py` - Multi-.env loading, accounts dict, helper methods
- Removal of `api_keys` and `api_keys_coding` fields (breaking change)
- Environment variable schema documentation

### Definition of Done
- [x] AccountConfig model with validation and SecretStr
- [x] Settings class loads from both .env files with correct precedence
- [x] `accounts: Dict[str, AccountConfig]` field works correctly
- [x] Helper methods return expected values (get_account, get_accounts_by_provider, get_default_account)
- [x] Old `api_keys` and `api_keys_coding` fields removed
- [x] Secrets not leaked in __str__, __repr__, or logs
- [x] Invalid provider IDs raise ValidationError
- [x] All tests pass (pytest)
- [x] Code formatted with ruff

### Must Have

- Multi-.env file loading (repo directory + home directory at ~/.config/opencode-python/.env)
- AccountConfig Pydantic model with SecretStr for api_key
- ProviderID enum integration (reuse existing enum)
- Named accounts with string keys (dict lookup)
- Helper methods for account retrieval
- Lenient validation (warn only, don't reject invalid keys)
- Breaking change: remove api_keys and api_keys_coding fields

### Must NOT Have (Guardrails)

- UI or CLI commands for account management
- Account CRUD operations (create/update/delete via API)
- Credential rotation or refresh mechanisms
- Modifications to ProviderID enum or provider classes
- Custom exception types beyond Pydantic's
- Comprehensive credential validation (format checking, API validation)
- Configuration file encryption or secrets management
- Dynamic account addition/removal at runtime
- Support for credential files (JSON, YAML) - .env only
- New dependencies (pydantic-settings is already installed)

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task, regardless of test strategy.
>
> **FORBIDDEN** — acceptance criteria that require:
> - "User manually tests..." / "사용자가 직접 테스트..."
> - "User visually confirms..." / "사용자가 눈으로 확인..."
> - "User interacts with..." / "사용자가 직접 조작..."
> - "Ask user to verify..." / "사용자에게 확인 요청..."
> - ANY step where a human must perform an action
>
> **ALL verification is executed by the agent** using tools (Bash, Python REPL, etc.). No exceptions.

### Test Decision

- **Infrastructure exists**: YES (pytest with pytest-asyncio, pytest-cov)
- **Automated tests**: YES (Tests-after)
- **Framework**: pytest
- **Location**: `opencode_python/tests/` for settings module tests

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

> Whether tests are written or not, EVERY task MUST include Agent-Executed QA Scenarios.
> These describe how the executing agent DIRECTLY verifies the deliverable
> by running Python code, importing modules, and asserting expected behavior.
>
> **Each Scenario MUST Follow This Format:**

```
Scenario: [Descriptive name — what is being verified]
  Tool: Bash (Python REPL or pytest)
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact Python code to execute or pytest command to run]
    2. [Assertion or expected output check]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Output capture or test result]
```

**Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Python Modules** | Bash (Python REPL) | Import modules, instantiate classes, call methods, assert return values |
| **Settings/Config** | Bash (Python REPL) | Create Settings instance, check fields, verify precedence |
| **Type Safety** | Bash (Python REPL) | Pass invalid types, catch ValidationError, assert error messages |
| **Security** | Bash (Python REPL) | Print settings, assert secrets not leaked |

---

## Execution Strategy

### Parallel Execution Waves

> This task requires sequential execution due to breaking changes.
> Each task builds on the previous one.

```
Wave 1 (Start Immediately):
└── Task 1: Create provider_settings.py with AccountConfig model

Wave 2 (After Task 1):
├── Task 2: Update Settings class with multi-.env loading
├── Task 3: Add helper methods to Settings class
└── Task 4: Remove old api_keys fields (breaking change)

Wave 3 (After Wave 2):
├── Task 5: Write unit tests for AccountConfig
├── Task 6: Write unit tests for Settings class
└── Task 7: Write integration tests for multi-.env loading

Wave 4 (After Wave 3):
└── Task 8: Verify breaking change and run full test suite

Critical Path: Task 1 → Task 2 → Task 3 → Task 4 → Task 8
Parallel Speedup: Limited (sequential due to dependencies)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None (first task) |
| 2 | 1 | 4, 5 | 3 (both depend on 1) |
| 3 | 1 | 4, 6 | 2 (both depend on 1) |
| 4 | 2, 3 | 8 | None (sequential due to breaking change) |
| 5 | 1 | 8 | 6, 7 (all depend on 1) |
| 6 | 1 | 8 | 5, 7 (all depend on 1) |
| 7 | 2 | 8 | 5, 6 (all depend on 1/2) |
| 8 | 4, 5, 6, 7 | None | None (final task) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1 | delegate_task(category="quick", load_skills=[], run_in_background=false) |
| 2 | 2, 3 | delegate_task(category="quick", load_skills=[], run_in_background=false) - run sequentially |
| 3 | 4 | delegate_task(category="quick", load_skills=[], run_in_background=false) |
| 4 | 5, 6, 7 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=false) |
| 5 | 8 | delegate_task(category="unspecified-low", load_skills=[], run_in_background=false) |

---

## TODOs

- [x] 1. Create provider_settings.py with AccountConfig model

  **What to do**:
  - Create new file: `src/opencode_python/core/provider_settings.py`
  - Import required dependencies (BaseModel, Field, SecretStr, field_validator, model_validator, ProviderID)
  - Define AccountConfig class with fields:
    - `account_name: str` - Account identifier (e.g., "openai-prod")
    - `provider_id: ProviderID` - Type-safe provider enum
    - `api_key: SecretStr` - Secure credential storage
    - `model: str` - Model name (e.g., "gpt-4")
    - `base_url: Optional[str] = None` - Custom base URL
    - `options: Dict[str, Any]` - Provider-specific options
    - `is_default: bool = False` - Default account marker
  - Add validators:
    - `validate_api_key()` - Warn if len(v) < 32, but don't reject
    - `validate_account_name()` - Ensure not empty, strip whitespace
    - `validate_model()` - Ensure model is not empty

  **Must NOT do**:
  - Add UI or CLI for account management
  - Modify ProviderID enum (reuse existing)
  - Add comprehensive validation beyond type checking
  - Create custom exception types

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `quick`
    - Reason: Single file creation with straightforward Pydantic model, no complex logic
  - **Skills**: []
    - No special skills needed - Python file creation and Pydantic model implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (first task)
  - **Blocks**: Tasks 2, 3, 5, 6, 7 (depend on AccountConfig model)
  - **Blocked By**: None (can start immediately)

  **References**:

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `src/opencode_python/core/provider_config.py` - ProviderConfig dataclass structure (similar fields to replicate)
  - `src/opencode_python/providers/base.py:7-28` - ProviderID enum definition (import and reuse)
  - Existing Pydantic BaseModel patterns in codebase (search for "class.*BaseModel")

  **API/Type References** (contracts to implement against):
  - `src/opencode_python/providers/base.py:ProviderID` - Enum values to validate against

  **Documentation References** (specs and requirements):
  - Interview decisions: AccountConfig fields, validation strategy (lenient)

  **External References** (libraries and frameworks):
  - Official docs: https://docs.pydantic.dev/latest/concepts/validators/ - Field validator syntax
  - Official docs: https://docs.pydantic.dev/latest/concepts/fields/ - Field types and defaults
  - Official docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ - Settings integration

  **WHY Each Reference Matters** (explain the relevance):
  - `provider_config.py`: Shows existing provider configuration structure, helps maintain consistency
  - `providers/base.py`: Must import and reuse ProviderID enum, not create duplicate
  - Pydantic docs: Ensure correct validator syntax and field configuration

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.
  > REPLACE all placeholders with actual values from task context.

  - [ ] File created: `src/opencode_python/core/provider_settings.py`
  - [ ] Module imports successfully: `from opencode_python.core.provider_settings import AccountConfig`
  - [ ] AccountConfig instantiates with all fields
  - [ ] Field validator warns for short API keys (< 32 chars)
  - [ ] Field validator rejects empty account_name
  - [ ] Model validator rejects empty model
  - [ ] ProviderID enum validation works (invalid provider raises ValidationError)

  **Agent-Executed QA Scenarios (MANDATORY — per-scenario, ultra-detailed):**

  \`\`\`
  Scenario: AccountConfig model with valid data instantiates successfully
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py file exists
    Steps:
      1. python -c "
from opencode_python.core.provider_settings import AccountConfig
from opencode_python.providers.base import ProviderID

config = AccountConfig(
    account_name='openai-prod',
    provider_id=ProviderID.OPENAI,
    api_key='sk-proj-this-is-a-valid-length-api-key',
    model='gpt-4'
)
print('SUCCESS: AccountConfig created')
print(f'account_name={config.account_name}')
print(f'provider_id={config.provider_id}')
print(f'model={config.model}')
"
    Expected Result: SUCCESS message, all fields printed correctly
    Failure Indicators: ImportError, ValidationError, AttributeError
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: AccountConfig rejects empty account_name
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py file exists
    Steps:
      1. python -c "
from opencode_python.core.provider_settings import AccountConfig
from opencode_python.providers.base import ProviderID

try:
    config = AccountConfig(
        account_name='',  # Empty
        provider_id=ProviderID.OPENAI,
        api_key='sk-proj-valid-key',
        model='gpt-4'
    )
    print('FAIL: Should have raised ValidationError')
except Exception as e:
    print(f'SUCCESS: Validation error raised: {type(e).__name__}')
"
    Expected Result: SUCCESS message with ValidationError
    Failure Indicators: FAIL message (no validation occurred)
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: AccountConfig rejects empty model
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py file exists
    Steps:
      1. python -c "
from opencode_python.core.provider_settings import AccountConfig
from opencode_python.providers.base import ProviderID

try:
    config = AccountConfig(
        account_name='openai-prod',
        provider_id=ProviderID.OPENAI,
        api_key='sk-proj-valid-key',
        model=''  # Empty
    )
    print('FAIL: Should have raised ValidationError')
except Exception as e:
    print(f'SUCCESS: Validation error raised: {type(e).__name__}')
"
    Expected Result: SUCCESS message with ValidationError
    Failure Indicators: FAIL message (no validation occurred)
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: AccountConfig warns for short API key but accepts it
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py file exists
    Steps:
      1. python -c "
import warnings
from opencode_python.core.provider_settings import AccountConfig
from opencode_python.providers.base import ProviderID

# Capture warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    config = AccountConfig(
        account_name='openai-test',
        provider_id=ProviderID.OPENAI,
        api_key='short',  # Too short
        model='gpt-4'
    )
    if len(w) > 0:
        print(f'SUCCESS: Warning raised: {w[0].message}')
    else:
        print('FAIL: Should have warned about short API key')
print(f'config.api_key={config.api_key}')  # Should show SecretStr
"
    Expected Result: SUCCESS message with UserWarning about short API key
    Failure Indicators: FAIL message (no warning)
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: AccountConfig rejects invalid ProviderID
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py file exists
    Steps:
      1. python -c "
from opencode_python.core.provider_settings import AccountConfig

try:
    config = AccountConfig(
        account_name='invalid-account',
        provider_id='nonexistent_provider',  # Invalid
        api_key='sk-proj-valid-key',
        model='gpt-4'
    )
    print('FAIL: Should have raised ValidationError')
except Exception as e:
    print(f'SUCCESS: Validation error raised: {type(e).__name__}')
"
    Expected Result: SUCCESS message with ValidationError
    Failure Indicators: FAIL message (invalid provider accepted)
    Evidence: Python REPL output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Python REPL output for all scenarios saved to .sisyphus/evidence/task-1-*.txt

  **Commit**: YES
  - Message: `feat(core): add AccountConfig Pydantic model for multi-account provider settings`
  - Files: `src/opencode_python/core/provider_settings.py`
  - Pre-commit: None (implementation first, tests later)

---

- [x] 2. Update Settings class with multi-.env file loading and accounts field

  **What to do**:
  - Update `src/opencode_python/core/settings.py`
  - Add imports:
    - `from pathlib import Path`
    - `from typing import Dict, Optional`
    - `from opencode_python.core.provider_settings import AccountConfig`
    - `from opencode_python.providers.base import ProviderID`
  - Add new field: `accounts: Dict[str, AccountConfig] = Field(default_factory=dict)`
  - Update `model_config`:
    - Change `env_file` from single string to tuple:
      - First: `Path(__file__).parent.parent.parent / '.env'` (repo directory, lower priority)
      - Second: `Path.home() / '.config' / 'opencode-python' / '.env'` (home directory, higher priority)
    - Add `env_nested_delimiter='__'` (allow nested env vars)
  - Keep existing `api_key: SecretStr` field (backward compatibility)
  - Keep all other existing fields unchanged

  **Must NOT do**:
  - Remove `api_key: SecretStr` field (keep for backward compatibility)
  - Remove `provider_default` or `model_default` fields
  - Add helper methods yet (next task)
  - Modify other existing fields

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Settings class update with existing structure, just adding field and config
  - **Skills**: []
    - No special skills needed - Pydantic Settings configuration

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Tasks 4, 7 (depend on accounts field)
  - **Blocked By**: Task 1 (need AccountConfig model)

  **References**:
  - `src/opencode_python/core/settings.py:19-85` - Existing Settings class structure
  - `src/opencode_python/core/provider_settings.py` - AccountConfig model (new import)
  - Pydantic Settings docs: env_file tuple, env_nested_delimiter

  **Acceptance Criteria**:
  - [ ] Settings imports successfully with new imports
  - [ ] accounts field added to Settings class
  - [ ] model_config updated with env_file tuple
  - [ ] env_nested_delimiter='__' added to model_config
  - [ ] Settings loads without errors when both .env files exist
  - [ ] Settings loads without errors when only repo .env exists
  - [ ] Settings loads without errors when only home .env exists

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Settings class loads with multi-.env file configuration
    Tool: Bash (Python REPL)
    Preconditions: provider_settings.py exists, settings.py updated
    Steps:
      1. python -c "
from opencode_python.core.settings import Settings
from pathlib import Path

# Check model_config
config = Settings.model_config
print(f'env_file={config.get(\"env_file\")}')
print(f'env_nested_delimiter={config.get(\"env_nested_delimiter\")}')

# Verify it's a tuple
env_files = config.get('env_file')
print(f'env_files type={type(env_files).__name__}')
print(f'env_files count={len(env_files)}')
"
    Expected Result: env_file is tuple with 2 paths, env_nested_delimiter is '__'
    Failure Indicators: env_file is not tuple, env_nested_delimiter missing
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: Settings loads when only repo .env exists
    Tool: Bash (Python REPL)
    Preconditions: repo .env exists, home .env does not exist
    Steps:
      1. cd opencode_python && python -c "
from opencode_python.core.settings import settings
print('SUCCESS: Settings loaded')
print(f'accounts count={len(settings.accounts)}')
"
    Expected Result: SUCCESS message, accounts dict loaded
    Failure Indicators: FileNotFoundError, ImportError
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: Settings loads when no .env files exist
    Tool: Bash (Python REPL)
    Preconditions: No .env files
    Steps:
      1. cd opencode_python && python -c "
from opencode_python.core.settings import settings
print('SUCCESS: Settings loaded with no .env files')
print(f'accounts={settings.accounts}')
"
    Expected Result: SUCCESS message, accounts is empty dict
    Failure Indicators: FileNotFoundError (should gracefully skip missing files)
    Evidence: Python REPL output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Python REPL output for all scenarios

  **Commit**: YES
  - Message: `feat(core): update Settings with multi-.env file loading and accounts field`
  - Files: `src/opencode_python/core/settings.py`
  - Pre-commit: None

---

- [x] 3. Add helper methods to Settings class for account lookup

  **What to do**:
  - Update `src/opencode_python/core/settings.py`
  - Add method: `get_account(self, account_name: str) -> Optional[AccountConfig]`
    - Return `self.accounts.get(account_name)`
  - Add method: `get_accounts_by_provider(self, provider_id: ProviderID) -> Dict[str, AccountConfig]`
    - Return filtered dict of accounts where `account.provider_id == provider_id`
  - Add method: `get_default_account(self) -> Optional[AccountConfig]`
    - Iterate over accounts and return first where `is_default == True`
    - Return None if no default account found

  **Must NOT do**:
  - Add account CRUD methods (create/update/delete)
  - Add account switching logic
  - Add custom exception types
  - Modify other methods or fields

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Three simple helper methods with straightforward logic
  - **Skills**: []
    - No special skills needed - Python method implementation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 2)
  - **Blocks**: Task 4 (breaking change depends on complete Settings class)
  - **Blocked By**: Task 1 (need AccountConfig type)

  **References**:
  - `src/opencode_python/core/settings.py` - Add methods to this class
  - Interview decisions: Helper method signatures and behavior (get_account, get_accounts_by_provider, get_default_account)

  **Acceptance Criteria**:
  - [ ] get_account method returns account for valid name
  - [ ] get_account returns None for non-existent name
  - [ ] get_accounts_by_provider returns filtered dict for valid provider
  - [ ] get_accounts_by_provider returns empty dict for provider with no accounts
  - [ ] get_default_account returns account with is_default=True
  - [ ] get_default_account returns None when no default exists

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: get_account returns account for existing name
    Tool: Bash (Python REPL)
    Preconditions: Settings loaded with test account
    Steps:
      1. python -c "
from opencode_python.core.settings import settings
from opencode_python.core.provider_settings import AccountConfig

# Add test account via environment var
import os
os.environ['OPENCODE_PYTHON_ACCOUNTS__TEST__PROVIDER_ID'] = 'openai'
os.environ['OPENCODE_PYTHON_ACCOUNTS__TEST__API_KEY'] = 'sk-test-key'
os.environ['OPENCODE_PYTHON_ACCOUNTS__TEST__MODEL'] = 'gpt-4'

# Reload settings
from opencode_python.core.settings import Settings
test_settings = Settings()

account = test_settings.get_account('test')
if account:
    print(f'SUCCESS: Account found, model={account.model}')
else:
    print('FAIL: Account not found')
"
    Expected Result: SUCCESS message with account details
    Failure Indicators: FAIL message, account is None
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: get_account returns None for non-existent name
    Tool: Bash (Python REPL)
    Preconditions: Settings loaded
    Steps:
      1. python -c "
from opencode_python.core.settings import settings
account = settings.get_account('nonexistent_account')
if account is None:
    print('SUCCESS: None returned for non-existent account')
else:
    print('FAIL: Should have returned None')
"
    Expected Result: SUCCESS message
    Failure Indicators: FAIL message
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: get_accounts_by_provider returns filtered dict
    Tool: Bash (Python REPL)
    Preconditions: Settings loaded with multiple accounts
    Steps:
      1. python -c "
from opencode_python.core.settings import settings
from opencode_python.providers.base import ProviderID

# Add test accounts
import os
os.environ['OPENCODE_PYTHON_ACCOUNTS__OPENAI_ONE__PROVIDER_ID'] = 'openai'
os.environ['OPENCODE_PYTHON_ACCOUNTS__OPENAI_ONE__API_KEY'] = 'sk-key1'
os.environ['OPENCODE_PYTHON_ACCOUNTS__OPENAI_ONE__MODEL'] = 'gpt-4'
os.environ['OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_ONE__PROVIDER_ID'] = 'anthropic'
os.environ['OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_ONE__API_KEY'] = 'sk-ant-key'
os.environ['OPENCODE_PYTHON_ACCOUNTS__ANTHROPIC_ONE__MODEL'] = 'claude-4'

from opencode_python.core.settings import Settings
test_settings = Settings()

openai_accounts = test_settings.get_accounts_by_provider(ProviderID.OPENAI)
print(f'openai accounts count={len(openai_accounts)}')
print(f'openai account names={list(openai_accounts.keys())}')

anthropic_accounts = test_settings.get_accounts_by_provider(ProviderID.ANTHROPIC)
print(f'anthropic accounts count={len(anthropic_accounts)}')
print(f'anthropic account names={list(anthropic_accounts.keys())}')
"
    Expected Result: openai count=1, anthropic count=1, correct names
    Failure Indicators: Wrong counts, wrong names
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: get_default_account returns default account
    Tool: Bash (Python REPL)
    Preconditions: Settings loaded with default account
    Steps:
      1. python -c "
from opencode_python.core.settings import settings
from opencode_python.providers.base import ProviderID

import os
os.environ['OPENCODE_PYTHON_ACCOUNTS__DEFAULT_ACCOUNT__PROVIDER_ID'] = 'openai'
os.environ['OPENCODE_PYTHON_ACCOUNTS__DEFAULT_ACCOUNT__API_KEY'] = 'sk-key'
os.environ['OPENCODE_PYTHON_ACCOUNTS__DEFAULT_ACCOUNT__MODEL'] = 'gpt-4'
os.environ['OPENCODE_PYTHON_ACCOUNTS__DEFAULT_ACCOUNT__IS_DEFAULT'] = 'true'

from opencode_python.core.settings import Settings
test_settings = Settings()

default = test_settings.get_default_account()
if default:
    print(f'SUCCESS: Default account found: {default.account_name}')
else:
    print('FAIL: Default account not found')
"
    Expected Result: SUCCESS message with default account name
    Failure Indicators: FAIL message
    Evidence: Python REPL output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Python REPL output for all scenarios

  **Commit**: YES
  - Message: `feat(core): add helper methods for account lookup in Settings`
  - Files: `src/opencode_python/core/settings.py`
  - Pre-commit: None

---

- [x] 4. Remove old api_keys and api_keys_coding fields (breaking change)

  **What to do**:
  - Update `src/opencode_python/core/settings.py`
  - Remove field: `api_keys: Dict[str, SecretStr]`
  - Remove field: `api_keys_coding: Dict[str, SecretStr]`
  - Keep field: `api_key: SecretStr` (single key for backward compatibility)
  - Verify no other references to removed fields in settings.py

  **Must NOT do**:
  - Remove `api_key: SecretStr` field (keep for single-key use cases)
  - Modify other fields or methods
  - Add migration logic (breaking change, user responsibility)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple field removal, breaking change but straightforward
  - **Skills**: []
    - No special skills needed - remove lines from Python class

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after helper methods)
  - **Blocks**: Task 8 (verification requires breaking change complete)
  - **Blocked By**: Tasks 2, 3 (Settings class must be complete)

  **References**:
  - `src/opencode_python/core/settings.py:27-28` - Lines to remove
  - Interview decision: Breaking change - remove api_keys and api_keys_coding

  **Acceptance Criteria**:
  - [ ] api_keys field removed from Settings class
  - [ ] api_keys_coding field removed from Settings class
  - [ ] api_key field still present (backward compatibility)
  - [ ] Settings loads without errors
  - [ ] Accessing settings.api_keys raises AttributeError

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Old api_keys field is removed and raises AttributeError
    Tool: Bash (Python REPL)
    Preconditions: settings.py updated with fields removed
    Steps:
      1. python -c "
from opencode_python.core.settings import Settings
test_settings = Settings()

try:
    _ = test_settings.api_keys
    print('FAIL: api_keys field still exists')
except AttributeError:
    print('SUCCESS: api_keys field removed (raises AttributeError)')
"
    Expected Result: SUCCESS message (AttributeError raised)
    Failure Indicators: FAIL message (field still exists)
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: Old api_keys_coding field is removed and raises AttributeError
    Tool: Bash (Python REPL)
    Preconditions: settings.py updated with fields removed
    Steps:
      1. python -c "
from opencode_python.core.settings import Settings
test_settings = Settings()

try:
    _ = test_settings.api_keys_coding
    print('FAIL: api_keys_coding field still exists')
except AttributeError:
    print('SUCCESS: api_keys_coding field removed (raises AttributeError)')
"
    Expected Result: SUCCESS message (AttributeError raised)
    Failure Indicators: FAIL message (field still exists)
    Evidence: Python REPL output
  \`\`\`

  \`\`\`
  Scenario: Single api_key field still exists for backward compatibility
    Tool: Bash (Python REPL)
    Preconditions: settings.py updated
    Steps:
      1. python -c "
from opencode_python.core.settings import Settings
test_settings = Settings()

if hasattr(test_settings, 'api_key'):
    print(f'SUCCESS: api_key field exists: {type(test_settings.api_key).__name__}')
else:
    print('FAIL: api_key field removed')
"
    Expected Result: SUCCESS message
    Failure Indicators: FAIL message (field removed)
    Evidence: Python REPL output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Python REPL output for all scenarios

  **Commit**: YES
  - Message: `refactor(core): remove api_keys and api_keys_coding fields (breaking change)`
  - Files: `src/opencode_python/core/settings.py`
  - Pre-commit: None (tests will verify breaking change)

---

- [x] 5. Write unit tests for AccountConfig model

  **What to do**:
  - Create test file: `opencode_python/tests/test_account_config.py`
  - Write test class: `TestAccountConfig`
  - Test cases:
    - `test_valid_account_config_instantiates` - All fields, valid data
    - `test_account_name_validation_rejects_empty` - Empty account_name raises ValidationError
    - `test_account_name_validation_strips_whitespace` - Leading/trailing spaces removed
    - `test_model_validation_rejects_empty` - Empty model raises ValidationError
    - `test_api_key_validation_warns_short_keys` - Short keys (< 32 chars) warn but don't reject
    - `test_api_key_validation_accepts_valid_keys` - Valid keys accepted
    - `test_provider_id_validation_rejects_invalid` - Invalid ProviderID raises ValidationError
    - `test_provider_id_validation_accepts_valid` - Valid ProviderID accepted
    - `test_base_url_optional_field` - base_url can be None or string
    - `test_options_field_dict` - options is dict
    - `test_is_default_field` - is_default bool field
  - Use pytest assertions
  - Mock/fixture: None needed (pure model validation)

  **Must NOT do**:
  - Add integration tests with file system (separate task)
  - Test Settings class (separate task)
  - Add custom fixtures beyond pytest defaults

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Unit test writing, straightforward test cases for Pydantic model
  - **Skills**: []
    - No special skills needed - pytest test implementation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 6, 7)
  - **Blocks**: Task 8 (full test suite)
  - **Blocked By**: Task 1 (need AccountConfig model)

  **References**:
  - `opencode_python/tests/test_config.py` - Existing test patterns (class-based organization)
  - `src/opencode_python/core/provider_settings.py` - AccountConfig model (what to test)
  - pytest docs: https://docs.pytest.org/ - Test structure and assertions

  **Acceptance Criteria**:
  - [ ] Test file created: `opencode_python/tests/test_account_config.py`
  - [ ] All 9 test cases written
  - [ ] pytest test_account_config.py runs without errors
  - [ ] All tests pass (green)

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Unit tests for AccountConfig all pass
    Tool: Bash (pytest)
    Preconditions: test_account_config.py exists
    Steps:
      1. cd opencode_python && python -m pytest tests/test_account_config.py -v
    Expected Result: All tests pass (green), 0 failures
    Failure Indicators: Test failures, import errors
    Evidence: pytest output
  \`\`\`

  **Evidence to Capture**:
  - [ ] pytest output saved to .sisyphus/evidence/task-5-pytest.txt

  **Commit**: YES
  - Message: `test(core): add unit tests for AccountConfig model`
  - Files: `opencode_python/tests/test_account_config.py`
  - Pre-commit: `python -m pytest tests/test_account_config.py -v`

---

- [x] 6. Write unit tests for Settings class

  **What to do**:
  - Create/update test file: `opencode_python/tests/test_settings_accounts.py`
  - Write test class: `TestSettingsAccounts`
  - Test cases:
    - `test_accounts_field_exists` - accounts field present in Settings
    - `test_accounts_field_default_empty_dict` - Default is empty dict
    - `test_get_account_returns_account_for_valid_name` - get_account returns AccountConfig
    - `test_get_account_returns_none_for_nonexistent` - get_account returns None
    - `test_get_accounts_by_provider_filters_correctly` - Returns filtered dict for provider
    - `test_get_accounts_by_provider_returns_empty_for_no_matches` - Empty dict if no matches
    - `test_get_default_account_returns_default` - Returns account with is_default=True
    - `test_get_default_account_returns_none_if_no_default` - None if no default
    - `test_multi_env_file_loading` - Both repo and home .env files loaded
    - `test_home_env_overrides_repo_env` - Home overrides repo for same account
    - `test_secret_str_redacts_in_str` - Secrets not leaked in str()
    - `test_secret_str_redacts_in_repr` - Secrets not leaked in repr()
  - Use pytest assertions
  - Use monkeypatch or os.environ for env var setup

  **Must NOT do**:
  - Test AccountConfig (separate file)
  - Test provider classes (out of scope)
  - Add integration tests with actual files (separate task)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Unit test writing, Settings class testing
  - **Skills**: []
    - No special skills needed - pytest test implementation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 5, 7)
  - **Blocks**: Task 8 (full test suite)
  - **Blocked By**: Task 1 (need AccountConfig)

  **References**:
  - `opencode_python/tests/test_config.py` - Existing Settings test patterns
  - `src/opencode_python/core/settings.py` - Settings class (what to test)

  **Acceptance Criteria**:
  - [ ] Test file created/updated: `opencode_python/tests/test_settings_accounts.py`
  - [ ] All 11 test cases written
  - [ ] pytest test_settings_accounts.py runs without errors
  - [ ] All tests pass (green)

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Unit tests for Settings accounts functionality all pass
    Tool: Bash (pytest)
    Preconditions: test_settings_accounts.py exists
    Steps:
      1. cd opencode_python && python -m pytest tests/test_settings_accounts.py -v
    Expected Result: All tests pass (green), 0 failures
    Failure Indicators: Test failures, import errors
    Evidence: pytest output
  \`\`\`

  **Evidence to Capture**:
  - [ ] pytest output saved to .sisyphus/evidence/task-6-pytest.txt

  **Commit**: YES
  - Message: `test(core): add unit tests for Settings accounts functionality`
  - Files: `opencode_python/tests/test_settings_accounts.py`
  - Pre-commit: `python -m pytest tests/test_settings_accounts.py -v`

---

- [x] 7. Write integration tests for multi-.env file loading

  **What to do**:
  - Create test file: `opencode_python/tests/test_multi_env_loading.py`
  - Write test class: `TestMultiEnvLoading`
  - Test cases:
    - `test_loads_from_repo_env_only` - Only repo .env exists
    - `test_loads_from_home_env_only` - Only home .env exists
    - `test_loads_from_both_envs` - Both repo and home .env exist
    - `test_home_env_overrides_repo_env_for_same_account` - Precedence: home > repo
    - `test_loads_with_no_env_files` - No .env files, empty accounts
    - `test_nested_env_vars_parse_correctly` - ACCOUNTS__OPENAI_PROD__API_KEY parses
    - `test_invalid_provider_id_raises_validation_error` - Invalid ProviderID in .env raises error
    - `test_env_vars_case_insensitive_for_prefix` - Lowercase/uppercase mixed works
  - Use pytest tmp_path fixture for creating temporary .env files
  - Clean up temporary files after each test

  **Must NOT do**:
  - Test AccountConfig or Settings methods (separate files)
  - Test provider integrations (out of scope)
  - Modify actual project .env files

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Integration test with file system, temporary files
  - **Skills**: []
    - No special skills needed - pytest with tmp_path fixture

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 5, 6)
  - **Blocks**: Task 8 (full test suite)
  - **Blocked By**: Task 2 (Settings must support multi-.env loading)

  **References**:
  - `tests/conftest.py` - Existing pytest fixtures
  - `tests/test_cli_integration.py` - Integration test patterns with temp files
  - pytest docs: https://docs.pytest.org/ - tmp_path fixture

  **Acceptance Criteria**:
  - [ ] Test file created: `opencode_python/tests/test_multi_env_loading.py`
  - [ ] All 8 test cases written
  - [ ] pytest test_multi_env_loading.py runs without errors
  - [ ] All tests pass (green)
  - [ ] Temporary files cleaned up

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Integration tests for multi-.env loading all pass
    Tool: Bash (pytest)
    Preconditions: test_multi_env_loading.py exists
    Steps:
      1. cd opencode_python && python -m pytest tests/test_multi_env_loading.py -v
    Expected Result: All tests pass (green), 0 failures
    Failure Indicators: Test failures, file cleanup issues
    Evidence: pytest output
  \`\`\`

  **Evidence to Capture**:
  - [ ] pytest output saved to .sisyphus/evidence/task-7-pytest.txt

  **Commit**: YES
  - Message: `test(core): add integration tests for multi-.env file loading`
  - Files: `opencode_python/tests/test_multi_env_loading.py`
  - Pre-commit: `python -m pytest tests/test_multi_env_loading.py -v`

---

- [x] 8. Verify breaking change and run full test suite

  **What to do**:
  - Verify all code references to old fields are updated
  - Run full test suite: `pytest opencode_python/tests/`
  - Run tests with coverage: `pytest --cov=opencode_python`
  - Check for any failing tests related to breaking change
  - Format code with ruff: `ruff check opencode_python/src/`
  - Format with ruff: `ruff format opencode_python/src/`
  - Verify test coverage is acceptable

  **Must NOT do**:
  - Modify tests beyond fixing breaking change failures
  - Change implementation (only verification)
  - Skip failing tests (must fix or update code)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Verification task, running existing tests, no new code
  - **Skills**: []
    - No special skills needed - pytest, ruff commands

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final task)
  - **Blocks**: None (final verification)
  - **Blocked By**: Tasks 4, 5, 6, 7 (all implementation and tests complete)

  **References**:
  - All test files in `opencode_python/tests/`
  - `opencode_python/pyproject.toml` - Test and lint configuration

  **Acceptance Criteria**:
  - [ ] pytest opencode_python/tests/ runs without import errors
  - [ ] All existing tests still pass (no regressions)
  - [ ] All new tests pass (AccountConfig, Settings accounts, multi-env loading)
  - [ ] No AttributeError related to api_keys or api_keys_coding
  - [ ] Code passes ruff format check
  - [ ] Code formatted with ruff
  - [ ] Test coverage report generated

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Full test suite passes with no regressions
    Tool: Bash (pytest)
    Preconditions: All tasks completed
    Steps:
      1. cd opencode_python && python -m pytest tests/ -v
    Expected Result: All tests pass (green), no failures
    Failure Indicators: Test failures, AttributeError from breaking change
    Evidence: pytest output
  \`\`\`

  \`\`\`
  Scenario: Code passes ruff format check
    Tool: Bash (ruff)
    Preconditions: ruff installed (in dev dependencies)
    Steps:
      1. cd opencode_python && ruff check src/opencode_python/
    Expected Result: No formatting errors
    Failure Indicators: Ruff errors/warnings
    Evidence: ruff output
  \`\`\`

  \`\`\`
  Scenario: Code formatted with ruff
    Tool: Bash (ruff)
    Preconditions: ruff installed
    Steps:
      1. cd opencode_python && ruff format src/opencode_python/
    Expected Result: Code formatted, changes (if any)
    Failure Indicators: Ruff errors
    Evidence: ruff output
  \`\`\`

  **Evidence to Capture**:
  - [ ] pytest output saved to .sisyphus/evidence/task-8-pytest.txt
  - [ ] ruff check output saved to .sisyphus/evidence/task-8-ruff-check.txt
  - [ ] ruff format output saved to .sisyphus/evidence/task-8-ruff-format.txt

  **Commit**: YES (if any formatting changes needed)
  - Message: `style(core): format code with ruff`
  - Files: Any formatted files
  - Pre-commit: `ruff check src/opencode_python/`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(core): add AccountConfig Pydantic model for multi-account provider settings` | `src/opencode_python/core/provider_settings.py` | None (implementation first) |
| 2 | `feat(core): update Settings with multi-.env file loading and accounts field` | `src/opencode_python/core/settings.py` | None |
| 3 | `feat(core): add helper methods for account lookup in Settings` | `src/opencode_python/core/settings.py` | None |
| 4 | `refactor(core): remove api_keys and api_keys_coding fields (breaking change)` | `src/opencode_python/core/settings.py` | None |
| 5 | `test(core): add unit tests for AccountConfig model` | `opencode_python/tests/test_account_config.py` | `pytest tests/test_account_config.py -v` |
| 6 | `test(core): add unit tests for Settings accounts functionality` | `opencode_python/tests/test_settings_accounts.py` | `pytest tests/test_settings_accounts.py -v` |
| 7 | `test(core): add integration tests for multi-.env file loading` | `opencode_python/tests/test_multi_env_loading.py` | `pytest tests/test_multi_env_loading.py -v` |
| 8 | `style(core): format code with ruff` (if needed) | Any formatted files | `ruff check src/opencode_python/` |

---

## Success Criteria

### Verification Commands
```bash
# Run all tests
cd opencode_python && pytest tests/ -v

# Run with coverage
pytest --cov=opencode_python --cov-report=term-missing

# Check code formatting
ruff check src/opencode_python/
```

### Final Checklist
- [x] AccountConfig model created with validation
- [x] Settings class loads from both .env files with correct precedence
- [x] Helper methods work correctly (get_account, get_accounts_by_provider, get_default_account)
- [x] Old api_keys and api_keys_coding fields removed
- [x] Secrets not leaked in __str__, __repr__, or logs
- [x] All unit tests pass
- [x] All integration tests pass
- [x] Code formatted with ruff
- [x] No test regressions
- [x] Breaking change verified (old fields raise AttributeError)
