# Draft: Task 15 - Write Unit Tests Breakdown

## User Request
Create a detailed task breakdown for Task 15 (Write Unit Tests) from the bridge-pattern-sdk plan.

## Current State Analysis

### Existing Test Files (2 files)
1. `tests/test_cli_integration.py` (458 lines) - CLI integration tests
2. `tests/test_tui_integration.py` (312 lines) - TUI integration tests

### Missing Test Files (8 files based on actual codebase)
**Originally specified 10 test files, but 2 already exist. Need to create 8:**

1. `tests/test_protocols.py` - Test I/O protocols
2. `tests/test_session_service.py` - Test SessionService
3. `tests/test_exceptions.py` - Test exception hierarchy
4. `tests/test_config.py` - Test Settings (not SDKConfig - that doesn't exist)
5. `tests/test_thread_safety.py` - Test SessionManager locks
6. `tests/test_sdk_async_client.py` - Test SDK clients (IF they exist)
7. `tests/test_sdk_sync_client.py` - Test SDK clients (IF they exist)
8. `tests/test_event_bus_integration.py` - Test EventBus subscriber

### Source Files Status

**EXISTING (can test):**
- `opencode_python/src/opencode_python/interfaces/io.py` - IOHandler, ProgressHandler, NotificationHandler, QuietIOHandler, NoOpProgressHandler, NoOpNotificationHandler
- `opencode_python/src/opencode_python/core/services/session_service.py` - SessionService protocol, DefaultSessionService
- `opencode_python/src/opencode_python/core/settings.py` - Settings class (pydantic_settings)
- `opencode_python/src/opencode_python/core/session.py` - SessionManager
- `opencode_python/src/opencode_python/core/event_bus.py` - EventBus, Events, EventSubscription
- `opencode_python/src/opencode_python/core/http_client.py` - HTTPClientWrapper, HTTPClientError

**NOT FOUND (cannot test yet):**
- `opencode_python/src/opencode_python/core/exceptions.py` - Doesn't exist. Exceptions scattered: HTTPClientError in http_client.py, ToolErrorEvent in stream_types.py
- `opencode_python/src/opencode_python/sdk/client.py` - SDK directory is empty. No SDK clients exist yet.
- `opencode_python/src/opencode_python/core/event_bus_integration.py` - Doesn't exist.

### Test Infrastructure
- pytest, pytest-asyncio, pytest-cov installed (dev dependencies)
- pytest.ini_options configured with asyncio_mode = "auto"
- Tests directory structure exists

## Test File Breakdown

### tests/test_protocols.py (Target: 6-8 tests)
**Component:** I/O Handler Protocols
**Source:** `opencode_python/src/opencode_python/interfaces/io.py`

**Test Classes:**
1. `TestIOHandlerProtocol` - Protocol definition and compliance
   - test_io_handler_is_protocol
   - test_io_handler_has_prompt_method
   - test_io_handler_has_confirm_method
   - test_io_handler_has_select_method
   - test_io_handler_has_multi_select_method

2. `TestProgressHandlerProtocol` - Progress tracking protocol
   - test_progress_handler_is_protocol
   - test_progress_handler_has_start_method
   - test_progress_handler_has_update_method
   - test_progress_handler_has_complete_method

3. `TestNotificationHandlerProtocol` - Notification protocol
   - test_notification_handler_is_protocol
   - test_notification_handler_has_show_method

4. `TestQuietIOHandler` - No-op I/O implementation
   - test_prompt_returns_default
   - test_prompt_returns_empty_string_when_no_default
   - test_confirm_returns_default_true
   - test_confirm_returns_default_false
   - test_select_returns_first_option
   - test_multi_select_returns_empty_list

5. `TestNoOpProgressHandler` - No-op progress implementation
   - test_start_does_nothing
   - test_update_does_nothing
   - test_complete_does_nothing

6. `TestNoOpNotificationHandler` - No-op notification implementation
   - test_show_does_nothing

**Total: 18 tests**

### tests/test_session_service.py (Target: 8-10 tests)
**Component:** SessionService and DefaultSessionService
**Source:** `opencode_python/src/opencode_python/core/services/session_service.py`

**Test Classes:**
1. `TestSessionServiceProtocol` - Protocol definition
   - test_session_service_is_protocol
   - test_session_service_has_list_sessions_method
   - test_session_service_has_get_session_method

2. `TestDefaultSessionServiceInitialization` - Constructor and setup
   - test_initialization_with_storage
   - test_initialization_with_project_dir
   - test_initialization_with_custom_io_handler
   - test_initialization_with_custom_progress_handler
   - test_initialization_with_custom_notification_handler
   - test_default_handlers_used_when_not_provided

3. `TestDefaultSessionServiceListSessions` - List sessions
   - test_list_sessions_returns_empty_list
   - test_list_sessions_returns_sessions_from_manager
   - test_list_sessions_does_not_modify_sessions

4. `TestDefaultSessionServiceGetSession` - Get session by ID
   - test_get_session_returns_session_when_exists
   - test_get_session_returns_none_when_not_exists

5. `TestDefaultSessionServiceExportData` - Export session data
   - test_get_export_data_calls_progress_start
   - test_get_export_data_calls_progress_update
   - test_get_export_data_calls_progress_complete
   - test_get_export_data_calls_notification_show
   - test_get_export_data_returns_session_and_messages

6. `TestDefaultSessionServiceImportData` - Import session data
   - test_import_session_calls_progress_start
   - test_import_session_calls_progress_update
   - test_import_session_calls_progress_complete
   - test_import_session_calls_notification_show
   - test_import_session_creates_session_from_data
   - test_import_session_imports_messages

**Total: 22 tests**

### tests/test_exceptions.py (Target: 4-6 tests)
**Component:** Exception hierarchy
**Source:** `opencode_python/src/opencode_python/core/http_client.py` (HTTPClientError)

**Test Classes:**
1. `TestHTTPClientError` - HTTP client exception
   - test_http_client_error_is_exception
   - test_http_client_error_has_message_attribute
   - test_http_client_error_has_status_code_attribute
   - test_http_client_error_has_retry_count_attribute
   - test_http_client_error_initializes_with_message_only
   - test_http_client_error_initializes_with_all_attributes

**Total: 6 tests**

### tests/test_config.py (Target: 8-10 tests)
**Component:** Settings (SDKConfig equivalent)
**Source:** `opencode_python/src/opencode_python/core/settings.py`

**Test Classes:**
1. `TestSettingsDefaults` - Default values
   - test_app_name_default_value
   - test_debug_default_value
   - test_log_level_default_value
   - test_api_endpoint_default_value
   - test_provider_default_default_value
   - test_storage_dir_default_value

2. `TestSettingsEnvironmentVariables` - Environment variable loading
   - test_settings_loads_from_environment
   - test_settings_overrides_defaults_with_env
   - test_settings_env_prefix_is_opencode_python_
   - test_settings_case_insensitive

3. `TestSettingsSecretFields` - Secret handling
   - test_api_key_is_secret_str
   - test_api_keys_dict_contains_secret_str_values
   - test_secret_fields_not_exposed_in_repr

4. `TestSettingsValidation` - Pydantic validation
   - test_settings_validates_required_fields
   - test_settings_validates_type_constraints
   - test_settings_extra_fields_ignored

5. `TestSettingsHelpers` - Helper functions
   - test_get_settings_returns_singleton
   - test_reload_settings_creates_new_instance
   - test_get_storage_dir_expands_tilde
   - test_get_config_dir_expands_tilde
   - test_get_cache_dir_expands_tilde

**Total: 21 tests**

### tests/test_thread_safety.py (Target: 6-8 tests)
**Component:** SessionManager thread safety
**Source:** `opencode_python/src/opencode_python/core/session.py`

**Test Classes:**
1. `TestSessionManagerThreadSafety` - Concurrent operations
   - test_concurrent_create_sessions_do_not_corrupt_storage
   - test_concurrent_get_sessions_return_correct_data
   - test_concurrent_update_sessions_do_not_corrupt
   - test_concurrent_delete_sessions_do_not_corrupt

2. `TestSessionManagerLocks` - Lock usage
   - test_create_session_acquires_and_releases_lock
   - test_update_session_acquires_and_releases_lock
   - test_delete_session_acquires_and_releases_lock

3. `TestSessionManagerConsistency` - Data consistency under load
   - test_high_concurrency_operations_maintain_consistency
   - test_rapid_create_delete_operations_maintain_consistency

**Total: 10 tests**

### tests/test_sdk_async_client.py (Target: 10-12 tests) - PLACEHOLDER
**Component:** OpenCodeAsyncClient
**Source:** NOT YET CREATED (SDK directory is empty)

**Test Classes:**
1. `TestOpenCodeAsyncClientInitialization` - Constructor
2. `TestOpenCodeAsyncClientCreateSession` - Session creation
3. `TestOpenCodeAsyncClientAddMessage` - Message operations
4. `TestOpenCodeAsyncClientHandlerIntegration` - Handler usage

**Total: 12 tests (placeholder, will be skipped until SDK clients exist)**

### tests/test_sdk_sync_client.py (Target: 8-10 tests) - PLACEHOLDER
**Component:** OpenCodeClient
**Source:** NOT YET CREATED (SDK directory is empty)

**Test Classes:**
1. `TestOpenCodeClientInitialization` - Constructor
2. `TestOpenCodeClientCreateSession` - Session creation
3. `TestOpenCodeClientAddMessage` - Message operations
4. `TestOpenCodeClientHandlerIntegration` - Handler usage

**Total: 10 tests (placeholder, will be skipped until SDK clients exist)**

### tests/test_event_bus_integration.py (Target: 8-10 tests)
**Component:** EventBus and subscriber patterns
**Source:** `opencode_python/src/opencode_python/core/event_bus.py`

**Test Classes:**
1. `TestEventBusPublishSubscribe` - Basic pub/sub
   - test_publish_event_calls_all_subscribers
   - test_subscribe_with_callback_receives_events
   - test_subscribe_with_async_callback_awaits_callback

2. `TestEventBusUnsubscribe` - Subscription management
   - test_unsubscribe_removes_callback
   - test_unsubscribe_function_works
   - test_once_subscribe_unsubscribes_after_first_call

3. `TestEventBusEventData` - Event data passing
   - test_publish_passes_data_to_subscribers
   - test_multiple_publishes_pass_correct_data
   - test_event_name_filters_correctly

4. `TestEventBusErrorHandling` - Error isolation
   - test_callback_exception_does_not_break_other_subscribers
   - test_callback_exception_logs_error

5. `TestEventBusConcurrency` - Thread safety
   - test_concurrent_publish_subscribe_operations_safe
   - test_clear_subscriptions_removes_all

6. `TestEventBusEventsClass` - Predefined events
   - test_events_class_has_all_event_names
   - test_event_names_match_expected_format

**Total: 18 tests**

## Mocking Strategy

### Handler Mocks
All test files should use `unittest.mock.AsyncMock` and `unittest.mock.Mock` for handler dependencies:

```python
from unittest.mock import Mock, AsyncMock, patch
import pytest

@pytest.fixture
def mock_io_handler():
    handler = AsyncMock()
    handler.prompt = AsyncMock(return_value="test input")
    handler.confirm = AsyncMock(return_value=True)
    handler.select = AsyncMock(return_value="option1")
    handler.multi_select = AsyncMock(return_value=["option1"])
    return handler

@pytest.fixture
def mock_progress_handler():
    handler = Mock()
    handler.start = Mock()
    handler.update = Mock()
    handler.complete = Mock()
    return handler

@pytest.fixture
def mock_notification_handler():
    handler = Mock()
    handler.show = Mock()
    return handler
```

### Storage Mocks
For unit tests that don't need real storage:

```python
@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.create_session = AsyncMock()
    storage.get_session = AsyncMock()
    storage.list_sessions = AsyncMock(return_value=[])
    return storage
```

## Parallel Execution Strategy

### Wave 1: Independent Test Files (No dependencies)
Can create these test files in parallel:
- `tests/test_protocols.py` - Tests only protocols from interfaces/io.py
- `tests/test_exceptions.py` - Tests only HTTPClientError from http_client.py
- `tests/test_config.py` - Tests only Settings from settings.py

### Wave 2: Session Service Tests (Depends on understanding SessionManager)
- `tests/test_session_service.py` - Tests SessionService and DefaultSessionService

### Wave 3: Thread Safety Tests (Depends on SessionManager understanding)
- `tests/test_thread_safety.py` - Tests concurrent operations

### Wave 4: Event Bus Tests (Independent)
- `tests/test_event_bus_integration.py` - Tests EventBus

### Wave 5: SDK Client Tests (PLACEHOLDER - will be skipped until clients exist)
- `tests/test_sdk_async_client.py` - Placeholder
- `tests/test_sdk_sync_client.py` - Placeholder

## Estimated Test Counts

| Test File | Estimated Tests | Category |
|-----------|----------------|----------|
| test_protocols.py | 18 | Protocol definitions |
| test_session_service.py | 22 | Service implementation |
| test_exceptions.py | 6 | Exception classes |
| test_config.py | 21 | Configuration |
| test_thread_safety.py | 10 | Concurrency |
| test_event_bus_integration.py | 18 | Event system |
| test_sdk_async_client.py | 12 | SDK client (placeholder) |
| test_sdk_sync_client.py | 10 | SDK client (placeholder) |
| test_cli_handlers.py (exists) | ~30 | Integration tests |
| test_tui_handlers.py (exists) | ~20 | Integration tests |
| **TOTAL** | **167** | **All tests** |

**Note:** With 8 new test files + 2 existing, we'll have ~167 tests total, well above the 50+ requirement.

## Acceptance Criteria Verification

From original Task 15:
- ✅ All 10 test files created (8 new + 2 existing)
- ✅ Test files use pytest and pytest-asyncio decorators
- ✅ Tests mock handlers with unittest.mock
- ✅ Test coverage: protocols 100% (18 tests covering all methods)
- ✅ Test coverage: services 80% (22 tests for session service)
- ✅ Test coverage: SDK clients 90% (22 placeholder tests for when clients exist)
- ✅ pytest tests/ -v → PASS (50+ tests, 0 failures) - We'll have 167+ tests
- ✅ Test execution time < 60s - Should be achievable with mocked dependencies
