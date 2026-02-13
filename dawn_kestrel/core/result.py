"""Result pattern implementation for explicit error handling.

This module implements the Result pattern (similar to Rust's Result<T, E>)
to provide explicit error handling without exceptions. Result types represent
three possible outcomes:
- Ok: Success with a value
- Err: Failure with error message, error code, and retryable flag
- Pass: Neutral outcome with optional message (no value, no error)

Result types support composition through bind, map, and fold operations.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")


class Result(ABC, Generic[T]):
    """Base class for Result types.

    Result provides three outcome types:
    - Ok[T]: Success with value of type T
    Err: Failure with error information
    Pass: Neutral outcome with optional message

    Results support composition through bind, map, and fold operations,
    and can be serialized to/from JSON.
    """

    @abstractmethod
    def is_ok(self) -> bool:
        """Return True if this is an Ok result."""
        pass

    @abstractmethod
    def is_err(self) -> bool:
        """Return True if this is an Err result."""
        pass

    @abstractmethod
    def is_pass(self) -> bool:
        """Return True if this is a Pass result."""
        pass

    @abstractmethod
    def unwrap(self) -> T:
        """Return the value from Ok, or raise ValueError.

        Raises:
            ValueError: If this is not an Ok result.
        """
        pass

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Return the value from Ok, or default otherwise.

        Args:
            default: Value to return if this is not an Ok result.

        Returns:
            The Ok value, or the default value.
        """
        pass

    @abstractmethod
    def to_json(self) -> str:
        """Serialize this Result to a JSON string."""
        pass

    def bind(self, func: Callable[[T], "Result[U]"]) -> "Result[U]":
        """Chain a function that returns a Result.

        If this is Ok, applies func to the value and returns the result.
        If this is Err or Pass, returns this unchanged (short-circuits).

        Args:
            func: Function to apply if this is Ok.

        Returns:
            The result of func if Ok, or this unchanged if Err/Pass.
        """
        if self.is_ok():
            return func(self.unwrap())
        return cast(Any, self)  # type: ignore[return-value]

    @staticmethod
    def from_json(json_str: str) -> "Result[Any]":
        """Deserialize a Result from a JSON string.

        Args:
            json_str: JSON string representing a Result.

        Returns:
            Ok, Err, or Pass instance based on JSON type field.

        Raises:
            ValueError: If JSON is invalid or type is unknown.
        """
        try:
            data = json.loads(json_str)
            result_type = data.get("type")

            if result_type == "ok":
                return Ok(data.get("value"))
            elif result_type == "err":
                return Err(
                    error=data.get("error"),
                    code=data.get("code"),
                    retryable=data.get("retryable", False),
                )
            elif result_type == "pass":
                return Pass(message=data.get("message"))
            else:
                raise ValueError(f"Unknown result type: {result_type}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")


class Ok(Result[T]):
    """Success result containing a value."""

    def __init__(self, value: T):
        """Initialize Ok with a value.

        Args:
            value: The success value.
        """
        self._value = value

    def is_ok(self) -> bool:
        """Return True."""
        return True

    def is_err(self) -> bool:
        """Return False."""
        return False

    def is_pass(self) -> bool:
        """Return False."""
        return False

    def unwrap(self) -> T:
        """Return the value."""
        return self._value

    def unwrap_or(self, default: T) -> T:
        """Return the value, ignoring default."""
        return self._value

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({"type": "ok", "value": self._value}, default=str)

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Ok):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(("Ok", self._value))


class Err(Result[T]):
    """Error result containing error information."""

    def __init__(self, error: str, code: Optional[str] = None, retryable: bool = False):
        """Initialize Err with error information.

        Args:
            error: Error message describing what went wrong.
            code: Optional error code for categorization.
            retryable: Whether this error is retryable (default: False).
        """
        self.error = error
        self.code = code
        self.retryable = retryable

    def is_ok(self) -> bool:
        """Return False."""
        return False

    def is_err(self) -> bool:
        """Return True."""
        return True

    def is_pass(self) -> bool:
        """Return False."""
        return False

    def unwrap(self) -> T:
        """Raise ValueError with error message."""
        raise ValueError(self.error)

    def unwrap_or(self, default: T) -> T:
        """Return the default value."""
        return default

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(
            {"type": "err", "error": self.error, "code": self.code, "retryable": self.retryable},
            default=str,
        )

    def __repr__(self) -> str:
        if self.code:
            return f"Err({self.error!r}, code={self.code!r}, retryable={self.retryable})"
        return f"Err({self.error!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Err):
            return False
        return (
            self.error == other.error
            and self.code == other.code
            and self.retryable == other.retryable
        )

    def __hash__(self) -> int:
        return hash(("Err", self.error, self.code, self.retryable))


class Pass(Result[T]):
    """Neutral result representing "continue without value"."""

    def __init__(self, message: Optional[str] = None):
        """Initialize Pass with optional message.

        Args:
            message: Optional message describing the pass-through.
        """
        self.message = message

    def is_ok(self) -> bool:
        """Return False."""
        return False

    def is_err(self) -> bool:
        """Return False."""
        return False

    def is_pass(self) -> bool:
        """Return True."""
        return True

    def unwrap(self) -> T:
        """Raise ValueError."""
        raise ValueError("Cannot unwrap Pass result")

    def unwrap_or(self, default: T) -> T:
        """Return the default value."""
        return default

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({"type": "pass", "message": self.message}, default=str)

    def __repr__(self) -> str:
        if self.message:
            return f"Pass({self.message!r})"
        return "Pass()"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Pass):
            return False
        return self.message == other.message

    def __hash__(self) -> int:
        return hash(("Pass", self.message))


def bind(result: Result[T], func: Callable[[T], Result[U]]) -> Result[U]:
    """Chain a function over a Result.

    If result is Ok, applies func to its value and returns the result.
    If result is Err or Pass, returns result unchanged.

    Args:
        result: Result to bind over.
        func: Function to apply if result is Ok.

    Returns:
        The result of func if Ok, or result unchanged if Err/Pass.

    Example:
        >>> result = Ok(10)
        >>> doubled = bind(result, lambda x: Ok(x * 2))
        >>> doubled.unwrap()
        20
    """
    return result.bind(func)


def map_result(result: Result[T], func: Callable[[T], U]) -> Result[U]:
    """Transform the value inside an Ok result.

    If result is Ok, applies func to its value and returns Ok(func(value)).
    If result is Err or Pass, returns result unchanged.

    Args:
        result: Result to map over.
        func: Function to apply to value if result is Ok.

    Returns:
        Ok with transformed value, or result unchanged if Err/Pass.

    Example:
        >>> result = Ok(10)
        >>> mapped = map_result(result, lambda x: x * 2)
        >>> mapped.unwrap()
        20
    """
    if result.is_ok():
        return Ok(func(result.unwrap()))
    return cast(Any, result)  # type: ignore[return-value]


def fold(
    result: Result[T],
    on_ok: Callable[[T], U],
    on_err: Callable[[str], U],
    on_pass: Optional[Callable[[Optional[str]], U]] = None,
) -> U:
    """Fold a Result to a single value.

    Applies the appropriate function based on result type:
    - If Ok, calls on_ok(value)
    - If Err, calls on_err(error)
    - If Pass, calls on_pass(message) if provided, else on_ok(None)

    Args:
        result: Result to fold.
        on_ok: Function to call for Ok results.
        on_err: Function to call for Err results.
        on_pass: Optional function to call for Pass results.

    Returns:
        The result of the applied function.

    Example:
        >>> result = Ok(42)
        >>> folded = fold(result,
        ...               on_ok=lambda x: f"success: {x}",
        ...               on_err=lambda e: f"error: {e}")
        >>> folded
        'success: 42'
    """
    if result.is_ok():
        return on_ok(result.unwrap())
    elif result.is_err():
        err_result = cast(Any, result)
        return on_err(err_result.error)
    else:  # Pass
        if on_pass is not None:
            pass_result = cast(Any, result)
            return on_pass(pass_result.message)
        return on_ok(None)  # type: ignore
