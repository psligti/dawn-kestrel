import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, List, Optional


class TraversalMode(str, Enum):
    BFS = "breadth_first"
    DFS = "depth_first"
    ADAPTIVE = "adaptive"


class DelegationStopReason(str, Enum):
    COMPLETED = "completed"
    CONVERGED = "converged"
    BUDGET_EXHAUSTED = "budget"
    STAGNATION = "stagnation"
    DEPTH_LIMIT = "depth_limit"
    BREADTH_LIMIT = "breadth_limit"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class DelegationBudget:
    max_depth: int = 3
    max_breadth: int = 5
    max_total_agents: int = 20
    max_wall_time_seconds: float = 300.0
    max_iterations: int = 10
    stagnation_threshold: int = 3

    def __post_init__(self):
        if self.max_depth <= 0:
            raise ValueError(f"max_depth must be > 0, got {self.max_depth}")
        if self.max_breadth <= 0:
            raise ValueError(f"max_breadth must be > 0, got {self.max_breadth}")
        if self.max_total_agents <= 0:
            raise ValueError(f"max_total_agents must be > 0, got {self.max_total_agents}")
        if self.max_wall_time_seconds <= 0:
            raise ValueError(f"max_wall_time_seconds must be > 0, got {self.max_wall_time_seconds}")
        if self.max_iterations <= 0:
            raise ValueError(f"max_iterations must be > 0, got {self.max_iterations}")
        if self.stagnation_threshold <= 0:
            raise ValueError(f"stagnation_threshold must be > 0, got {self.stagnation_threshold}")


@dataclass
class DelegationConfig:
    mode: TraversalMode = TraversalMode.BFS
    budget: DelegationBudget = field(default_factory=DelegationBudget)
    check_convergence: bool = True
    evidence_keys: List[str] = field(default_factory=lambda: ["result", "findings"])
    on_agent_spawn: Optional[Callable[[str, int], Awaitable[None]]] = None
    on_agent_complete: Optional[Callable[[str, Any], Awaitable[None]]] = None
    on_convergence_check: Optional[Callable[[List[Any]], Awaitable[bool]]] = None


@dataclass
class DelegationContext:
    root_task_id: str
    current_depth: int = 0
    total_agents_spawned: int = 0
    active_agents: int = 0
    completed_agents: int = 0
    results: List[Any] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    iteration_count: int = 0
    novelty_signatures: List[str] = field(default_factory=list)
    stagnation_count: int = 0

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time


@dataclass
class DelegationResult:
    success: bool
    stop_reason: DelegationStopReason
    results: List[Any]
    errors: List[Exception]
    total_agents: int
    max_depth_reached: int
    elapsed_seconds: float
    iterations: int
    converged: bool
    stagnation_detected: bool
    final_novelty_signature: Optional[str] = None
