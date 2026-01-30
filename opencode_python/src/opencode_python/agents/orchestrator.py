"""
Phase 3: Multi-Agent Orchestration - AgentOrchestrator.

Coordinates multiple agents with delegation, parallel execution,
task status tracking, and hierarchical sub-task management.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import asyncio
import logging
from threading import Lock
from dataclasses import dataclass

from opencode_python.core.agent_task import AgentTask, TaskStatus, create_agent_task
from opencode_python.core.agent_types import (
    AgentResult,
    SessionManagerLike,
)
from opencode_python.core.event_bus import bus, Events
from opencode_python.agents.runtime import AgentRuntime


logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """
    Result wrapper for task execution.

    Couples AgentTask with its AgentResult and execution metadata.
    """
    task: AgentTask
    """The task that was executed"""

    result: Optional[AgentResult] = None
    """Result from agent execution"""

    error: Optional[str] = None
    """Error message if execution failed"""

    started_at: float = 0.0
    """Start timestamp (epoch seconds)"""

    completed_at: float = 0.0
    """Completion timestamp (epoch seconds)"""


class AgentOrchestrator:
    """
    Coordinate multiple agents with delegation and parallel execution.

    Manages task lifecycle, tracks active tasks and results,
    supports hierarchical sub-task delegation, and emits events
    for task lifecycle monitoring.

    Features:
    - Thread-safe task management (Lock-protected)
    - Parallel execution of independent agents
    - Hierarchical sub-task support via parent_id
    - Event emission for task lifecycle
    - Integration with AgentRuntime for execution
    - In-memory tracking (no external queue required)
    """

    def __init__(
        self,
        agent_runtime: AgentRuntime,
    ):
        """
        Initialize AgentOrchestrator.

        Args:
            agent_runtime: AgentRuntime instance for task execution
        """
        self.agent_runtime = agent_runtime

        self._tasks: Dict[str, AgentTask] = {}
        self._results: Dict[str, TaskResult] = {}
        self._task_lock = Lock()

    async def delegate_task(
        self,
        task: AgentTask,
        session_id: str,
        user_message: str,
        session_manager: SessionManagerLike,
        tools,
        session,
    ) -> str:
        """
        Delegate a task to an agent via AgentRuntime.

        Executes the task and stores the result. Emits task lifecycle events.

        Args:
            task: AgentTask to execute
            session_id: Session ID for execution
            user_message: User message to process
            session_manager: SessionManager instance
            tools: ToolRegistry for the session
            session: Session object

        Returns:
            Task ID

        Raises:
            ValueError: If agent not found
        """
        import time
        from opencode_python.tools.framework import ToolRegistry

        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Task {task.task_id} is not pending: {task.status}")

        with self._task_lock:
            self._tasks[task.task_id] = task

        await bus.publish(Events.TASK_STARTED, {
            "task_id": task.task_id,
            "agent_name": task.agent_name,
            "session_id": session_id,
            "parent_id": task.parent_id,
        })
        logger.info(f"Task started: {task.task_id} -> {task.agent_name}")

        try:
            task.status = TaskStatus.RUNNING

            from opencode_python.tools.framework import ToolRegistry

            if not isinstance(tools, ToolRegistry):
                raise ValueError("tools must be a ToolRegistry instance")

            result = await self.agent_runtime.execute_agent(
                agent_name=task.agent_name,
                session_id=session_id,
                user_message=user_message,
                session_manager=session_manager,
                tools=tools,
                skills=task.skill_names,
                options=task.options,
            )

            task.status = TaskStatus.COMPLETED
            task.result_id = task.task_id
            task.result_agent_name = result.agent_name

            task_result = TaskResult(
                task=task,
                result=result,
                started_at=time.time() - result.duration,
                completed_at=time.time(),
            )

            with self._task_lock:
                self._results[task.task_id] = task_result

            await bus.publish(Events.TASK_COMPLETED, {
                "task_id": task.task_id,
                "agent_name": task.agent_name,
                "session_id": session_id,
                "duration": result.duration,
            })
            logger.info(
                f"Task completed: {task.task_id} -> {task.agent_name} "
                f"in {result.duration:.2f}s"
            )

            return task.task_id

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

            task_result = TaskResult(
                task=task,
                result=None,
                error=str(e),
                started_at=0.0,
                completed_at=0.0,
            )

            with self._task_lock:
                self._results[task.task_id] = task_result

            await bus.publish(Events.TASK_FAILED, {
                "task_id": task.task_id,
                "agent_name": task.agent_name,
                "session_id": session_id,
                "error": str(e),
            })
            logger.error(f"Task failed: {task.task_id} -> {e}")

            raise

    async def run_parallel_agents(
        self,
        tasks: List[AgentTask],
        session_id: str,
        user_messages: List[str],
        session_manager: SessionManagerLike,
        tools_list,
        session,
    ) -> List[str]:
        """
        Run multiple agents in parallel.

        Executes independent tasks concurrently. All tasks must be independent
        (no dependencies between them).

        Args:
            tasks: List of AgentTask to execute
            session_id: Session ID for execution
            user_messages: List of user messages (one per task)
            session_manager: SessionManager instance
            tools_list: List of ToolRegistry (one per task)
            session: Session object

        Returns:
            List of task IDs

        Raises:
            ValueError: If tasks and messages lengths don't match
        """
        if len(tasks) != len(user_messages):
            raise ValueError(
                f"Number of tasks ({len(tasks)}) must match "
                f"number of messages ({len(user_messages)})"
            )

        task_ids = []

        coroutines = [
            self.delegate_task(
                task=tasks[i],
                session_id=session_id,
                user_message=user_messages[i],
                session_manager=session_manager,
                tools=tools_list[i] if isinstance(tools_list, list) else tools_list,
                session=session,
            )
            for i in range(len(tasks))
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel task {tasks[i].task_id} failed: {result}")
            else:
                task_ids.append(result)

        return task_ids

    async def cancel_tasks(self, task_ids: List[str]) -> int:
        """
        Cancel running or pending tasks.

        Marks tasks as CANCELLED. Cannot cancel already completed tasks.

        Args:
            task_ids: List of task IDs to cancel

        Returns:
            Number of tasks cancelled
        """
        cancelled_count = 0

        with self._task_lock:
            for task_id in task_ids:
                task = self._tasks.get(task_id)
                if task and task.is_active():
                    task.status = TaskStatus.CANCELLED
                    cancelled_count += 1

                    await bus.publish(Events.TASK_CANCELLED, {
                        "task_id": task_id,
                        "agent_name": task.agent_name,
                    })
                    logger.info(f"Task cancelled: {task_id}")

        return cancelled_count

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get status of a task.

        Args:
            task_id: Task ID to query

        Returns:
            TaskStatus if found, None otherwise
        """
        with self._task_lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get result of a task.

        Args:
            task_id: Task ID to query

        Returns:
            TaskResult if found, None otherwise
        """
        with self._task_lock:
            return self._results.get(task_id)

    def get_active_tasks(self) -> List[AgentTask]:
        """
        Get all active (pending or running) tasks.

        Returns:
            List of active tasks
        """
        with self._task_lock:
            return [t for t in self._tasks.values() if t.is_active()]

    def get_child_tasks(self, parent_id: str) -> List[AgentTask]:
        """
        Get all child tasks of a parent task.

        Args:
            parent_id: Parent task ID

        Returns:
            List of child tasks
        """
        with self._task_lock:
            return [
                t for t in self._tasks.values()
                if t.parent_id == parent_id
            ]

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[AgentTask]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status_filter: Optional status filter

        Returns:
            List of tasks
        """
        with self._task_lock:
            tasks = list(self._tasks.values())

            if status_filter:
                tasks = [t for t in tasks if t.status == status_filter]

            return tasks

    def list_results(self) -> List[TaskResult]:
        """
        List all task results.

        Returns:
            List of TaskResult
        """
        with self._task_lock:
            return list(self._results.values())

    def clear_completed_tasks(self) -> int:
        """
        Clear completed task data from memory.

        Keeps only active (pending/running) tasks in memory.
        Useful for memory management in long-running orchestrators.

        Returns:
            Number of tasks cleared
        """
        cleared_count = 0

        with self._task_lock:
            task_ids_to_remove = []
            result_ids_to_remove = []

            for task_id, task in self._tasks.items():
                if task.is_complete():
                    task_ids_to_remove.append(task_id)

            for result_id in self._results:
                task = self._tasks.get(result_id)
                if task and task.is_complete():
                    result_ids_to_remove.append(result_id)

            for task_id in task_ids_to_remove:
                del self._tasks[task_id]
                cleared_count += 1

            for result_id in result_ids_to_remove:
                del self._results[result_id]

        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} completed tasks from memory")

        return cleared_count


def create_agent_orchestrator(agent_runtime: AgentRuntime) -> AgentOrchestrator:
    """
    Factory function to create AgentOrchestrator.

    Args:
        agent_runtime: AgentRuntime instance for task execution

    Returns:
        New AgentOrchestrator instance
    """
    return AgentOrchestrator(agent_runtime=agent_runtime)
