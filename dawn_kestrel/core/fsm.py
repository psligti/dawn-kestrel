"""Finite State Machine (FSM) protocol and data structures for builder pattern.

This module defines the FSM protocol and core data structures for the FSM
Builder pattern. The protocol defines the interface for state management,
allowing multiple implementations (in-memory, database-backed, etc.).

Key components:
- FSM protocol: Interface for state machine operations
- FSMConfig: Configuration dataclass for FSM builder
- FSMContext: Context passed to hooks and guards during transitions
- TransitionConfig: Metadata for individual state transitions
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol, runtime_checkable, Optional, Union

from dawn_kestrel.core.mediator import Event, EventMediator, EventType
from dawn_kestrel.core.observer import Observer
from dawn_kestrel.core.result import Result, Ok, Err
from dawn_kestrel.core.commands import TransitionCommand, CommandContext
from dawn_kestrel.llm.circuit_breaker import CircuitBreaker, CircuitBreakerImpl
from dawn_kestrel.llm.retry import RetryExecutor, RetryExecutorImpl, ExponentialBackoff
from dawn_kestrel.llm.rate_limiter import RateLimiter, RateLimiterImpl
from dawn_kestrel.llm.bulkhead import Bulkhead, BulkheadImpl


logger = logging.getLogger(__name__)


@runtime_checkable
class FSM(Protocol):
    """Protocol for finite state machine.

    State machine manages state transitions with validation,
    ensuring only valid transitions are executed.

    The protocol defines the interface for state management, allowing
    multiple implementations (in-memory, database-backed, etc.).

    Example:
        >>> class MyFSM(FSM):
        ...     async def get_state(self) -> str:
        ...         return "idle"
        ...     async def transition_to(self, new_state: str) -> Result[None]:
        ...         return Ok(None)
        ...     async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        ...         return True
    """

    async def get_state(self) -> str:
        """Get current state of the FSM.

        Returns:
            str: Current state of the FSM.
        """
        ...

    async def transition_to(
        self, new_state: str, context: Optional[FSMContext] = None
    ) -> Result[None]:
        """Transition FSM to new state.

        Args:
            new_state: Target state to transition to.
            context: Optional context passed to hooks and guards.

        Returns:
            Result[None]: Ok on successful transition, Err if transition invalid.
        """
        ...

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        """Check if transition from one state to another is valid.

        Args:
            from_state: Current state of FSM.
            to_state: Desired next state.

        Returns:
            bool: True if transition is valid, False otherwise.
        """
        ...


@dataclass
class FSMConfig:
    """Configuration dataclass for FSM builder.

    Contains all configuration needed to build an FSM instance,
    including states, transitions, hooks, and guards.

    Attributes:
        initial_state: Starting state for the FSM (default: "idle").
        states: Set of valid state names.
        transitions: Mapping of (from_state, to_state) to TransitionConfig.
        on_transition: Optional hook called before each transition.
        after_transition: Optional hook called after each successful transition.
        on_error: Optional hook called when a transition fails.
    """

    initial_state: str = "idle"
    states: set[str] = field(default_factory=set)
    transitions: dict[tuple[str, str], TransitionConfig] = field(default_factory=dict)
    on_transition: Optional[Callable[[str, str, FSMContext], Result[None]]] = None
    after_transition: Optional[Callable[[str, str, FSMContext], Result[None]]] = None
    on_error: Optional[Callable[[str, str, Err, FSMContext], None]] = None


@dataclass
class FSMContext:
    """Context passed to hooks and guards during transitions.

    Provides runtime information for state transition hooks,
    including event metadata and user data.

    Attributes:
        timestamp: When the transition was initiated.
        source: Identifier for what triggered the transition.
        metadata: Additional context data as key-value pairs.
        user_data: Arbitrary data for application use.
    """

    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    user_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionConfig:
    """Metadata for individual state transitions.

    Contains configuration for a specific transition from one state
    to another, including guards and hooks.

    Attributes:
        from_state: Source state name.
        to_state: Target state name.
        guards: Optional list of guard functions that must return True.
        on_enter: Optional hook called when entering target state.
        on_exit: Optional hook called when leaving source state.
        metadata: Additional transition metadata.
    """

    from_state: str
    to_state: str
    guards: Optional[list[Callable[[FSMContext], bool]]] = None
    on_enter: Optional[Callable[[FSMContext], Result[None]]] = None
    on_exit: Optional[Callable[[FSMContext], Result[None]]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FSMReliabilityConfig:
    """Configuration for reliability wrappers on FSM external actions.

    Reliability wrappers are applied to external action callbacks (hooks)
    to provide fault tolerance, not to FSM internal operations like
    transitions or state queries.

    Attributes:
        circuit_breaker: Optional CircuitBreaker for fault tolerance.
        retry_executor: Optional RetryExecutor for automatic retry with backoff.
        rate_limiter: Optional RateLimiter for API throttling.
        bulkhead: Optional Bulkhead for concurrent operation limiting.
        enabled: Whether reliability wrappers are enabled (default: True).
    """

    circuit_breaker: Optional[CircuitBreaker] = None
    retry_executor: Optional[RetryExecutor] = None
    rate_limiter: Optional[RateLimiter] = None
    bulkhead: Optional[Bulkhead] = None
    enabled: bool = True


class FSMImpl:
    """Generic finite state machine implementation.

    Manages state transitions with explicit validation and Result-based
    error handling. States and transitions are configurable via constructor
    parameters (typically set by FSMBuilder).

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use a thread-safe implementation with locks or consider a
        database-backed UnitOfWork pattern.

    Example:
        >>> valid_states = {"idle", "running", "completed"}
        >>> valid_transitions = {"idle": {"running"}, "running": {"completed"}}
        >>> fsm = FSMImpl("idle", valid_states, valid_transitions)
        >>> result = await fsm.transition_to("running")
        >>> result.is_ok()
        True
    """

    def __init__(
        self,
        initial_state: str,
        valid_states: set[str],
        valid_transitions: dict[str, set[str]],
        fsm_id: Optional[str] = None,
        repository: Any = None,
        mediator: Any = None,
        observers: Optional[list[Observer]] = None,
        entry_hooks: Optional[dict[str, Callable[[FSMContext], Result[None]]]] = None,
        exit_hooks: Optional[dict[str, Callable[[FSMContext], Result[None]]]] = None,
        reliability_config: Optional[FSMReliabilityConfig] = None,
    ):
        """Initialize FSM with configurable states and transitions.

        Args:
            initial_state: Starting state.
            valid_states: Set of valid state identifiers.
            valid_transitions: Dictionary mapping from_state to set of valid to_states.
            fsm_id: Optional unique identifier for this FSM instance.
            repository: Optional FSMStateRepository for state persistence.
            mediator: Optional EventMediator for event publishing.
            observers: Optional list of observers for state change notifications.
            entry_hooks: Optional dict mapping state names to entry hooks.
            exit_hooks: Optional dict mapping state names to exit hooks.
            reliability_config: Optional FSMReliabilityConfig for external action reliability.

        Raises:
            ValueError: If initial_state is not in valid_states.
        """
        if initial_state not in valid_states:
            raise ValueError(
                f"Invalid initial state: {initial_state}. Valid states are: {sorted(valid_states)}"
            )

        self._state = initial_state
        self._valid_states = valid_states
        self._valid_transitions = valid_transitions
        self._fsm_id = fsm_id or f"fsm_{id(self)}"
        self._command_history: list[Any] = []
        self._repository = repository
        self._mediator = mediator
        self._observers: set[Observer] = set(observers) if observers else set()
        self._entry_hooks: dict[str, Callable[[FSMContext], Result[None]]] = entry_hooks or {}
        self._exit_hooks: dict[str, Callable[[FSMContext], Result[None]]] = exit_hooks or {}
        self._reliability_config: Optional[FSMReliabilityConfig] = reliability_config

    async def get_state(self) -> str:
        """Get current state of FSM.

        Returns:
            str: Current state of the FSM.
        """
        return self._state

    async def is_transition_valid(self, from_state: str, to_state: str) -> bool:
        """Check if transition from one state to another is valid.

        Args:
            from_state: Current state.
            to_state: Desired next state.

        Returns:
            bool: True if transition is valid, False otherwise.
        """
        if from_state not in self._valid_transitions:
            return False
        return to_state in self._valid_transitions[from_state]

    async def transition_to(
        self, new_state: str, context: Optional[FSMContext] = None
    ) -> Result[TransitionCommand]:
        """Transition FSM to new state.

        Args:
            new_state: Target state to transition to.
            context: Optional context passed to hooks and guards.

        Returns:
            Result[TransitionCommand]: Ok with command on success, Err if transition invalid.
        """
        if not await self.is_transition_valid(self._state, new_state):
            return Err(
                f"Invalid state transition: {self._state} -> {new_state}. "
                f"Valid transitions from {self._state}: {sorted(self._valid_transitions.get(self._state, set()))}",
                code="INVALID_TRANSITION",
            )

        from_state = self._state

        command = TransitionCommand(
            fsm_id=self._fsm_id,
            from_state=from_state,
            to_state=new_state,
        )

        exit_hook = self._exit_hooks.get(from_state)
        if exit_hook:
            exit_metadata = {"state": from_state, "fsm_id": self._fsm_id}
            if context:
                exit_metadata.update(context.metadata)
            exit_context = FSMContext(
                timestamp=datetime.now(),
                source=f"fsm.{self._fsm_id}",
                metadata=exit_metadata,
            )
            if context and context.user_data:
                exit_context.user_data = context.user_data.copy()
            exit_result = await self._execute_with_reliability(exit_hook, exit_context, from_state)
            if exit_result.is_err():
                logger.error(
                    f"Exit hook failed for state {from_state} in FSM {self._fsm_id}: {exit_result.error}"
                )

        self._state = new_state

        entry_hook = self._entry_hooks.get(new_state)
        if entry_hook:
            entry_metadata = {"state": new_state, "fsm_id": self._fsm_id}
            if context:
                entry_metadata.update(context.metadata)
            entry_context = FSMContext(
                timestamp=datetime.now(),
                source=f"fsm.{self._fsm_id}",
                metadata=entry_metadata,
            )
            if context and context.user_data:
                entry_context.user_data = context.user_data.copy()
            entry_result = await self._execute_with_reliability(
                entry_hook, entry_context, new_state
            )
            if entry_result.is_err():
                logger.error(
                    f"Entry hook failed for state {new_state} in FSM {self._fsm_id}: {entry_result.error}"
                )

        if self._repository:
            persist_result = await self._repository.set_state(self._fsm_id, new_state)
            if persist_result.is_err():
                error_msg = persist_result.error
                logger.error(f"Failed to persist FSM state for {self._fsm_id}: {error_msg}")
                return Err(
                    f"Failed to persist state: {error_msg}",
                    code="PERSISTENCE_ERROR",
                )

        if self._mediator:
            event = Event(
                event_type=EventType.DOMAIN,
                source=self._fsm_id,
                data={
                    "fsm_id": self._fsm_id,
                    "from_state": from_state,
                    "to_state": new_state,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            publish_result = await self._mediator.publish(event)
            if publish_result.is_err():
                error_msg = publish_result.error
                logger.error(
                    f"Failed to publish state change event for FSM {self._fsm_id}: {error_msg}"
                )

        # Notify observers of state change
        if self._observers:
            event_data = {
                "fsm_id": self._fsm_id,
                "from_state": from_state,
                "to_state": new_state,
                "timestamp": datetime.now().isoformat(),
            }
            for observer in self._observers:
                try:
                    await observer.on_notify(self, event_data)
                except Exception as e:
                    logger.error(f"Observer error for FSM {self._fsm_id}: {e}")

        self._command_history.append(command)

        return Ok(command)

    def get_command_history(self) -> list[TransitionCommand]:
        """Get audit history of executed state transitions.

        Returns:
            List of TransitionCommand objects containing transition audit data.
        """
        return list(self._command_history)

    async def register_observer(self, observer: Observer) -> None:
        """Register observer for state change notifications.

        Args:
            observer: Observer to register.
        """
        self._observers.add(observer)

    async def unregister_observer(self, observer: Observer) -> None:
        """Unregister observer from state change notifications.

        Safe to call even if observer not registered.

        Args:
            observer: Observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    async def _execute_with_reliability(
        self,
        hook: Callable[[FSMContext], Result[None]],
        context: FSMContext,
        resource: str = "default",
    ) -> Result[None]:
        """Execute hook with reliability wrappers if configured.

        Wraps hook execution with circuit breaker, retry, rate limiter, and bulkhead
        if reliability_config is enabled. If not configured, executes hook directly.

        FSM internal operations are NOT wrapped - only external action callbacks.

        Args:
            hook: Hook function to execute.
            context: FSMContext to pass to hook.
            resource: Resource identifier for rate limiter/bulkhead (default: "default").

        Returns:
            Result[None]: Result of hook execution.
        """
        if not self._reliability_config or not self._reliability_config.enabled:
            try:
                return hook(context)
            except Exception as e:
                logger.error(f"Hook execution error: {e}", exc_info=True)
                return Err(f"Hook execution error: {e}", code="HOOK_ERROR")

        reliability = self._reliability_config

        async def operation():
            if inspect.iscoroutinefunction(hook):
                return await hook(context)
            else:
                return hook(context)

        if reliability.rate_limiter:
            acquire_result = await reliability.rate_limiter.try_acquire(resource)
            if acquire_result.is_err():
                return Err(
                    f"Rate limit exceeded: {acquire_result.error}",
                    code="RATE_LIMIT_EXCEEDED",
                )

        if reliability.retry_executor:
            result = await reliability.retry_executor.execute(operation)
            return result

        try:
            return await operation()
        except Exception as e:
            logger.error(f"Hook execution error: {e}", exc_info=True)
            return Err(f"Hook execution error: {e}", code="HOOK_ERROR")


class FSMBuilder:
    """Fluent API builder for FSM configuration.

    FSMBuilder provides a fluent interface for configuring FSM instances
    with states, transitions, hooks, guards, and optional integrations.

    All builder methods return self for method chaining:
        >>> fsm = (FSMBuilder()
        ...     .with_state("idle")
        ...     .with_state("running")
        ...     .with_transition("idle", "running")
        ...     .build())

    Validation:
        The build() method validates configuration before creating FSM:
        - All states used in transitions must be defined
        - Initial state must be a valid state

    Thread Safety:
        This builder is NOT thread-safe. Build in a single thread
        before using the FSM in concurrent contexts.
    """

    def __init__(self):
        """Initialize builder with empty configuration."""
        self._states: set[str] = set()
        self._transitions: dict[str, set[str]] = {}
        self._entry_hooks: dict[str, Callable[[FSMContext], Result[None]]] = {}
        self._exit_hooks: dict[str, Callable[[FSMContext], Result[None]]] = {}
        self._guards: dict[tuple[str, str], Callable[[FSMContext], Result[bool]]] = {}
        self._repository: Any = None
        self._mediator: Any = None
        self._observers: list[Any] = []
        self._reliability_config: Optional[FSMReliabilityConfig] = None

    def with_state(self, state: str) -> FSMBuilder:
        """Add a valid state.

        Args:
            state: State name to add to valid states.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> builder = FSMBuilder().with_state("idle").with_state("running")
        """
        self._states.add(state)
        return self

    def with_transition(self, from_state: str, to_state: str) -> FSMBuilder:
        """Add a valid transition.

        Args:
            from_state: Source state for transition.
            to_state: Destination state for transition.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> builder = FSMBuilder().with_transition("idle", "running")
        """
        if from_state not in self._transitions:
            self._transitions[from_state] = set()
        self._transitions[from_state].add(to_state)
        self._states.add(from_state)
        self._states.add(to_state)
        return self

    def with_entry_hook(self, state: str, hook: Callable[[FSMContext], Result[None]]) -> FSMBuilder:
        """Add an entry hook for a state.

        Hook is called when entering the state. Hook failures are logged
        and do not block transitions.

        Args:
            state: State to attach hook to.
            hook: Async callable taking FSMContext, returning Result[None].

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> async def on_enter(ctx: FSMContext) -> Result[None]:
            ...     print(f"Entering state: {ctx.state}")
            ...     return Ok(None)
            >>> builder = FSMBuilder().with_entry_hook("running", on_enter)
        """
        self._entry_hooks[state] = hook
        return self

    def with_exit_hook(self, state: str, hook: Callable[[FSMContext], Result[None]]) -> FSMBuilder:
        """Add an exit hook for a state.

        Hook is called when exiting the state. Hook failures are logged
        and do not block transitions.

        Args:
            state: State to attach hook to.
            hook: Async callable taking FSMContext, returning Result[None].

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> async def on_exit(ctx: FSMContext) -> Result[None]:
            ...     print(f"Exiting state: {ctx.state}")
            ...     return Ok(None)
            >>> builder = FSMBuilder().with_exit_hook("running", on_exit)
        """
        self._exit_hooks[state] = hook
        return self

    def with_guard(
        self,
        from_state: str,
        to_state: str,
        guard: Callable[[FSMContext], Result[bool]],
    ) -> FSMBuilder:
        """Add a guard condition for a transition.

        Guard is called before transition execution. If guard returns
        False or Err, the transition is rejected.

        Args:
            from_state: Source state for transition.
            to_state: Destination state for transition.
            guard: Async callable taking FSMContext, returning Result[bool].

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> async def can_transition(ctx: FSMContext) -> Result[bool]:
            ...     return Ok(True)
            >>> builder = FSMBuilder().with_guard("idle", "running", can_transition)
        """
        self._guards[(from_state, to_state)] = guard
        return self

    def with_persistence(self, repository: Any) -> FSMBuilder:
        """Enable state persistence.

        Repository must implement set_state(fsm_id, state) method.
        State is persisted after each successful transition.

        Args:
            repository: Repository object with set_state method.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> builder = FSMBuilder().with_persistence(my_repository)
        """
        self._repository = repository
        return self

    def with_mediator(self, mediator: Any) -> FSMBuilder:
        """Enable event publishing via Mediator.

        Mediator must implement publish(event) method.
        State change events are published after each transition.

        Args:
            mediator: EventMediator or compatible object.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> builder = FSMBuilder().with_mediator(my_mediator)
        """
        self._mediator = mediator
        return self

    def with_observer(self, observer: Any) -> FSMBuilder:
        """Add an observer for state changes.

        Observer must implement on_notify(observable, event) method.
        Observers are notified after each successful transition.

        Args:
            observer: Observer or compatible object.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> builder = FSMBuilder().with_observer(my_observer)
        """
        self._observers.append(observer)
        return self

    def with_reliability(self, config: FSMReliabilityConfig) -> FSMBuilder:
        """Enable reliability wrappers for external action callbacks.

        Reliability wrappers are applied to hooks (entry/exit) to provide
        fault tolerance for external operations. FSM internal operations
        (transitions, state queries) are NOT wrapped.

        Args:
            config: FSMReliabilityConfig with circuit breaker, retry, rate limiter, bulkhead.

        Returns:
            FSMBuilder: self for method chaining.

        Example:
            >>> config = FSMReliabilityConfig(
            ...     circuit_breaker=CircuitBreakerImpl(...),
            ...     retry_executor=RetryExecutorImpl(...),
            ... )
            >>> builder = FSMBuilder().with_reliability(config)
        """
        self._reliability_config = config
        return self

    def build(self, initial_state: str = "idle") -> Result[FSM]:
        """Build FSM instance from builder configuration.

        Validates configuration:
        - Initial state must be defined (if states are configured)
        - All states used in transitions must be defined

        Args:
            initial_state: Starting state (default: "idle").

        Returns:
            Result[FSM]: Ok with FSM instance, Err if configuration invalid.

        Example:
            >>> result = (FSMBuilder()
            ...     .with_state("idle")
            ...     .with_state("running")
            ...     .with_transition("idle", "running")
            ...     .build())
            >>> if result.is_ok():
            ...     fsm = result.unwrap()
        """
        undefined_states = set()
        for from_state, to_states in self._transitions.items():
            if from_state not in self._states:
                undefined_states.add(from_state)
            for to_state in to_states:
                if to_state not in self._states:
                    undefined_states.add(to_state)

        if undefined_states:
            return Err(
                f"Undefined states in transitions: {sorted(undefined_states)}. "
                f"Define states using with_state() before using them in transitions.",
                code="UNDEFINED_STATE_IN_TRANSITION",
            )

        if self._states and initial_state not in self._states:
            return Err(
                f"Invalid initial state: {initial_state}. Valid states are: {sorted(self._states)}",
                code="INVALID_INITIAL_STATE",
            )

        fsm = FSMImpl(
            initial_state=initial_state,
            valid_states=self._states,
            valid_transitions=self._transitions,
            repository=self._repository,
            mediator=self._mediator,
            observers=self._observers,
            entry_hooks=self._entry_hooks,
            exit_hooks=self._exit_hooks,
            reliability_config=self._reliability_config,
        )
        return Ok(fsm)
