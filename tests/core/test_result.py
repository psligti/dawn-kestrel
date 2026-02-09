"""Tests for Result pattern (Ok/Err/Pass).

Tests verify that Result types provide explicit error handling with:
- Ok: Success with value
- Err: Failure with error, error code, and retryable flag
- Pass: Neutral outcome with optional message
- Result helpers: bind, map, fold for composition
- JSON serialization for Results
- Thread-safe error context
"""

import json
import threading
from typing import Any, Generic, TypeVar
import pytest

# This import will fail initially - this is TDD RED phase
# from dawn_kestrel.core.result import Ok, Err, Pass, bind, map_result, fold


class TestResultTypeBasics:
    """Test basic Result type creation and methods."""

    def test_ok_result_creation(self):
        """Ok can be created with a value."""
        from dawn_kestrel.core.result import Ok

        result = Ok("success value")
        assert result.is_ok() is True
        assert result.is_err() is False
        assert result.is_pass() is False
        assert result.unwrap() == "success value"

    def test_err_result_creation(self):
        """Err can be created with error message."""
        from dawn_kestrel.core.result import Err

        result = Err("something went wrong")
        assert result.is_ok() is False
        assert result.is_err() is True
        assert result.is_pass() is False
        assert result.error == "something went wrong"

    def test_err_result_with_code(self):
        """Err can be created with error code."""
        from dawn_kestrel.core.result import Err

        result = Err("network error", code="ERR_NET_001")
        assert result.is_err() is True
        assert result.error == "network error"
        assert result.code == "ERR_NET_001"

    def test_err_result_with_retryable_flag(self):
        """Err can be created with retryable flag."""
        from dawn_kestrel.core.result import Err

        result = Err("timeout", code="ERR_TIMEOUT", retryable=True)
        assert result.is_err() is True
        assert result.retryable is True

    def test_err_result_default_retryable_is_false(self):
        """Err default retryable flag is False."""
        from dawn_kestrel.core.result import Err

        result = Err("error")
        assert result.retryable is False

    def test_pass_result_creation(self):
        """Pass can be created with optional message."""
        from dawn_kestrel.core.result import Pass

        result = Pass("continue without value")
        assert result.is_ok() is False
        assert result.is_err() is False
        assert result.is_pass() is True
        assert result.message == "continue without value"

    def test_pass_result_without_message(self):
        """Pass can be created without message."""
        from dawn_kestrel.core.result import Pass

        result = Pass()
        assert result.is_pass() is True
        assert result.message is None


class TestResultUnwrapMethods:
    """Test Result unwrap and safe unwrap methods."""

    def test_ok_unwrap_returns_value(self):
        """Ok.unwrap() returns the value."""
        from dawn_kestrel.core.result import Ok

        result = Ok(42)
        assert result.unwrap() == 42

    def test_ok_unwrap_or_returns_value(self):
        """Ok.unwrap_or() returns the value, ignoring default."""
        from dawn_kestrel.core.result import Ok

        result = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_err_unwrap_raises_exception(self):
        """Err.unwrap() raises an exception."""
        from dawn_kestrel.core.result import Err

        result = Err("error")
        with pytest.raises(ValueError) as exc_info:
            result.unwrap()
        assert "error" in str(exc_info.value)

    def test_err_unwrap_or_returns_default(self):
        """Err.unwrap_or() returns the default value."""
        from dawn_kestrel.core.result import Err

        result = Err("error")
        assert result.unwrap_or(42) == 42

    def test_pass_unwrap_raises_exception(self):
        """Pass.unwrap() raises an exception."""
        from dawn_kestrel.core.result import Pass

        result = Pass()
        with pytest.raises(ValueError):
            result.unwrap()

    def test_pass_unwrap_or_returns_default(self):
        """Pass.unwrap_or() returns the default value."""
        from dawn_kestrel.core.result import Pass

        result = Pass()
        assert result.unwrap_or(42) == 42


class TestResultBindComposition:
    """Test Result composition with bind."""

    def test_bind_chains_ok_results(self):
        """Bind chains Ok results successfully."""
        from dawn_kestrel.core.result import Ok, bind

        result = Ok(10)
        chained = result.bind(lambda x: Ok(x * 2))
        assert chained.is_ok() is True
        assert chained.unwrap() == 20

    def test_bind_stops_at_first_err(self):
        """Bind stops at first Err and returns it."""
        from dawn_kestrel.core.result import Ok, Err, bind

        result = Ok(10)
        chained = result.bind(lambda x: Err("error"))
        assert chained.is_err() is True
        assert chained.error == "error"

    def test_bind_passes_through_err(self):
        """Bind passes through Err unchanged."""
        from dawn_kestrel.core.result import Err, bind

        result = Err("initial error")
        chained = result.bind(lambda x: Ok(42))
        assert chained.is_err() is True
        assert chained.error == "initial error"

    def test_bind_with_multiple_chains(self):
        """Bind works with multiple chained operations."""
        from dawn_kestrel.core.result import Ok, bind

        result = Ok(2)
        chained = (
            result.bind(lambda x: Ok(x + 3)).bind(lambda x: Ok(x * 2)).bind(lambda x: Ok(x - 1))
        )
        assert chained.is_ok() is True
        assert chained.unwrap() == 9  # ((2 + 3) * 2) - 1 = 9


class TestResultMap:
    """Test Result map transformation."""

    def test_map_transforms_ok_value(self):
        """Map transforms Ok value."""
        from dawn_kestrel.core.result import Ok, map_result

        result = Ok(10)
        mapped = map_result(result, lambda x: x * 2)
        assert mapped.is_ok() is True
        assert mapped.unwrap() == 20

    def test_map_passes_through_err(self):
        """Map passes through Err unchanged."""
        from dawn_kestrel.core.result import Err, map_result

        result = Err("error")
        mapped = map_result(result, lambda x: x * 2)
        assert mapped.is_err() is True
        assert mapped.error == "error"

    def test_map_passes_through_pass(self):
        """Map passes through Pass unchanged."""
        from dawn_kestrel.core.result import Pass, map_result

        result = Pass("message")
        mapped = map_result(result, lambda x: x * 2)
        assert mapped.is_pass() is True
        assert mapped.message == "message"


class TestResultFold:
    """Test Result fold to single value."""

    def test_fold_with_ok_result(self):
        """Fold applies on_ok for Ok result."""
        from dawn_kestrel.core.result import Ok, fold

        result = Ok(42)
        folded = fold(result, on_ok=lambda x: f"success: {x}", on_err=lambda e: f"error: {e}")
        assert folded == "success: 42"

    def test_fold_with_err_result(self):
        """Fold applies on_err for Err result."""
        from dawn_kestrel.core.result import Err, fold

        result = Err("something failed")
        folded = fold(result, on_ok=lambda x: f"success: {x}", on_err=lambda e: f"error: {e}")
        assert folded == "error: something failed"

    def test_fold_with_pass_result(self):
        """Fold applies default for Pass result."""
        from dawn_kestrel.core.result import Pass, fold

        result = Pass("continue")
        folded = fold(
            result,
            on_ok=lambda x: f"success: {x}",
            on_err=lambda e: f"error: {e}",
            on_pass=lambda m: f"pass: {m}",
        )
        assert folded == "pass: continue"


class TestResultJSONSerialization:
    """Test Result JSON serialization."""

    def test_ok_serializes_to_json(self):
        """Ok Result can be serialized to JSON."""
        from dawn_kestrel.core.result import Ok

        result = Ok("success value")
        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["type"] == "ok"
        assert data["value"] == "success value"

    def test_err_serializes_to_json_with_all_fields(self):
        """Err Result serializes to JSON with error, code, retryable."""
        from dawn_kestrel.core.result import Err

        result = Err("network error", code="ERR_NET_001", retryable=True)
        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["type"] == "err"
        assert data["error"] == "network error"
        assert data["code"] == "ERR_NET_001"
        assert data["retryable"] is True

    def test_pass_serializes_to_json(self):
        """Pass Result can be serialized to JSON."""
        from dawn_kestrel.core.result import Pass

        result = Pass("continue")
        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["type"] == "pass"
        assert data["message"] == "continue"

    def test_ok_from_json(self):
        """Ok can be deserialized from JSON."""
        from dawn_kestrel.core.result import Ok, Result

        json_str = '{"type": "ok", "value": 42}'
        result = Result.from_json(json_str)

        assert isinstance(result, Ok)
        assert result.unwrap() == 42

    def test_err_from_json(self):
        """Err can be deserialized from JSON."""
        from dawn_kestrel.core.result import Err, Result

        json_str = '{"type": "err", "error": "error", "code": "ERR_001", "retryable": false}'
        result = Result.from_json(json_str)

        assert isinstance(result, Err)
        assert result.error == "error"
        assert result.code == "ERR_001"
        assert result.retryable is False

    def test_pass_from_json(self):
        """Pass can be deserialized from JSON."""
        from dawn_kestrel.core.result import Pass, Result

        json_str = '{"type": "pass", "message": "continue"}'
        result = Result.from_json(json_str)

        assert isinstance(result, Pass)
        assert result.message == "continue"


class TestResultThreadSafety:
    """Test Result thread-safe error context."""

    def test_multiple_threads_create_results_independently(self):
        """Multiple threads can create Results independently."""
        from dawn_kestrel.core.result import Ok, Err, Pass

        results = []
        errors = []

        def create_result(index):
            try:
                if index % 3 == 0:
                    results.append(Ok(f"ok_{index}"))
                elif index % 3 == 1:
                    results.append(Err(f"err_{index}", code=f"ERR_{index}"))
                else:
                    results.append(Pass(f"pass_{index}"))
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(100):
            t = threading.Thread(target=create_result, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 100

        # Verify all results are correct
        ok_count = sum(1 for r in results if r.is_ok())
        err_count = sum(1 for r in results if r.is_err())
        pass_count = sum(1 for r in results if r.is_pass())

        assert ok_count == 34  # 0, 3, 6, ..., 99
        assert err_count == 33  # 1, 4, 7, ..., 97
        assert pass_count == 33  # 2, 5, 8, ..., 98

    def test_result_bind_is_thread_safe(self):
        """Result bind operations are thread-safe."""
        from dawn_kestrel.core.result import Ok, bind

        results = []
        errors = []

        def process_value(value):
            try:
                result = Ok(value)
                chained = result.bind(lambda x: Ok(x * 2))
                results.append(chained.unwrap())
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            t = threading.Thread(target=process_value, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 50
        assert all(r == i * 2 for i, r in enumerate(results))


class TestResultTypeChecking:
    """Test Result type checking and isinstance."""

    def test_isinstance_checks_ok(self):
        """isinstance works for Ok."""
        from dawn_kestrel.core.result import Ok, Result

        result = Ok(42)
        assert isinstance(result, Ok)
        assert isinstance(result, Result)

    def test_isinstance_checks_err(self):
        """isinstance works for Err."""
        from dawn_kestrel.core.result import Err, Result

        result = Err("error")
        assert isinstance(result, Err)
        assert isinstance(result, Result)

    def test_isinstance_checks_pass(self):
        """isinstance works for Pass."""
        from dawn_kestrel.core.result import Pass, Result

        result = Pass()
        assert isinstance(result, Pass)
        assert isinstance(result, Result)

    def test_ok_not_instance_of_err_or_pass(self):
        """Ok is not instance of Err or Pass."""
        from dawn_kestrel.core.result import Ok, Err, Pass

        result = Ok(42)
        assert not isinstance(result, Err)
        assert not isinstance(result, Pass)

    def test_err_not_instance_of_ok_or_pass(self):
        """Err is not instance of Ok or Pass."""
        from dawn_kestrel.core.result import Ok, Err, Pass

        result = Err("error")
        assert not isinstance(result, Ok)
        assert not isinstance(result, Pass)

    def test_pass_not_instance_of_ok_or_err(self):
        """Pass is not instance of Ok or Err."""
        from dawn_kestrel.core.result import Ok, Err, Pass

        result = Pass()
        assert not isinstance(result, Ok)
        assert not isinstance(result, Err)
