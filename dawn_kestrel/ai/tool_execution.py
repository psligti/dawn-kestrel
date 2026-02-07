"""
Tool execution framework with AI integration.

Handles tool calls from AI providers, coordinates execution,
manages permissions, and updates tool state.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from dawn_kestrel.core.event_bus import bus, Events
from dawn_kestrel.tools.framework import ToolContext, ToolResult, ToolRegistry
from dawn_kestrel.core.models import ToolState, ToolPart
from dawn_kestrel.agents.tool_execution_tracker import ToolExecutionTracker


logger = logging.getLogger(__name__)


class ToolExecutionManager:
    """Manages tool execution from AI responses"""

    def __init__(
        self,
        session_id: str,
        tool_registry: Optional[ToolRegistry] = None,
        session_lifecycle: Optional[Any] = None,
        tracker: Optional[ToolExecutionTracker] = None,
    ):
        self.session_id = session_id
        self.active_calls: Dict[str, ToolContext] = {}
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self._lifecycle = session_lifecycle
        self.tracker = tracker
    
    async def execute_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_call_id: str,
        message_id: str,
        agent: str,
        model: str
    ) -> ToolResult:
        """Execute a single tool call from AI"""
        tool = self.tool_registry.get(tool_name)
        if not tool:
            logger.error(f"Tool {tool_name} not found")
            return ToolResult(
                title=f"Unknown tool: {tool_name}",
                output=f"Tool {tool_name} is not available",
                metadata={"error": f"unknown_tool: {tool_name}"}
            )
        
        logger.info(f"Executing tool: {tool_name} with input: {list(tool_input.keys()) if isinstance(tool_input, dict) else tool_input}")

        tool_context = ToolContext(
            session_id=self.session_id,
            message_id=message_id,
            agent=agent,
            call_id=tool_call_id,
            abort=asyncio.Event(),
            messages=[],
        )

        state = ToolState(
            status="pending",
            input=tool_input,
            time_start=None
        )

        tool_part = ToolPart(
            id=f"{self.session_id}_{tool_call_id}",
            session_id=self.session_id,
            message_id=message_id,
            part_type="tool",
            tool=tool_name,
            call_id=tool_call_id,
            state=state,
            source={"provider": model}
        )

        await bus.publish(Events.TOOL_STARTED, {
            "part_id": tool_part.id,
            "session_id": self.session_id,
            "tool": tool_name,
            "input": tool_input,
            "agent": agent,
            "model": model
        })

        if self.tracker:
            await self.tracker.log_execution(
                execution_id=tool_part.id,
                session_id=self.session_id,
                message_id=message_id,
                tool_id=tool_name,
                state=state,
                start_time=tool_context.time_created,
            )

        try:
            self.active_calls[tool_call_id] = tool_context

            result = await tool.execute(tool_input, tool_context)
            
            state.status = "completed"
            state.time_start = tool_context.time_created
            state.time_end = tool_context.time_finished
            state.output = result.output
            state.title = result.title
            state.metadata = result.metadata

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                    end_time=tool_context.time_finished,
                )

            await bus.publish(Events.TOOL_COMPLETED, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "result": result.output,
                "title": result.title,
                "metadata": result.metadata
            })

            return result

        except asyncio.CancelledError:
            logger.warning(f"Tool {tool_name} cancelled by user")
            state.status = "error"
            state.error = "Cancelled by user"

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                )

            await bus.publish(Events.TOOL_ERROR, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "error": state.error
            })

            return ToolResult(
                title="Cancelled",
                output="Cancelled by user",
                metadata={"error": "cancelled"}
            )

        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            state.status = "error"
            state.error = str(e)

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                )

            await bus.publish(Events.TOOL_ERROR, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "error": state.error
            })

            return ToolResult(
                title="Error",
                output=str(e),
                metadata={"error": str(e)}
            )

        finally:
            if tool_call_id in self.active_calls:
                del self.active_calls[tool_call_id]
    
    def _get_metadata(self, tool_context: ToolContext) -> Dict[str, Any]:
        return {
            "session_id": tool_context.session_id,
            "message_id": tool_context.message_id,
            "call_id": tool_context.call_id,
            "time_created": tool_context.time_created,
        }
    
    async def process_tool_stream(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_call_id: str,
        message_id: str,
        agent: str,
        model: str,
    ) -> ToolPart:
        """Process streaming tool execution from AI"""
        tool = self.tool_registry.get(tool_name)
        if not tool:
            logger.error(f"Tool {tool_name} not found")
            return ToolPart(
                id=f"{self.session_id}_{tool_call_id}",
                session_id=self.session_id,
                message_id=message_id,
                part_type="tool",
                tool=tool_name,
                call_id=tool_call_id,
                state=ToolState(
                    status="error",
                    error=f"Unknown tool: {tool_name}",
                    input=tool_input
                )
            )
        
        logger.info(f"Processing tool stream: {tool_name}")

        tool_context = ToolContext(
            session_id=self.session_id,
            message_id=message_id,
            agent=agent,
            call_id=tool_call_id,
            abort=asyncio.Event(),
            messages=[],
        )

        state = ToolState(
            status="running",
            input=tool_input,
            time_start=tool_context.time_created,
        )

        tool_part = ToolPart(
            id=f"{self.session_id}_{tool_call_id}",
            session_id=self.session_id,
            message_id=message_id,
            part_type="tool",
            tool=tool_name,
            call_id=tool_call_id,
            state=state,
            source={"provider": model}
        )

        await bus.publish(Events.TOOL_STARTED, {
            "part_id": tool_part.id,
            "session_id": self.session_id,
            "tool": tool_name,
            "input": tool_input,
            "agent": agent,
            "model": model
        })

        if self.tracker:
            await self.tracker.log_execution(
                execution_id=tool_part.id,
                session_id=self.session_id,
                message_id=message_id,
                tool_id=tool_name,
                state=state,
                start_time=tool_context.time_created,
            )

        try:
            self.active_calls[tool_call_id] = tool_context

            result = await tool.execute(tool_input, tool_context)
            
            state.status = "completed"
            state.time_end = tool_context.time_finished
            state.output = result.output
            state.title = result.title
            state.metadata = result.metadata

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                    end_time=tool_context.time_finished,
                )

            await bus.publish(Events.TOOL_COMPLETED, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "result": result.output,
                "title": result.title,
                "metadata": result.metadata
            })
            
        except asyncio.CancelledError:
            logger.warning(f"Tool {tool_name} cancelled during stream")
            state.status = "error"
            state.error = "Cancelled"

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                )

        except Exception as e:
            logger.error(f"Tool {tool_name} stream failed: {e}")
            state.status = "error"
            state.error = str(e)

            if self.tracker:
                await self.tracker.update_execution(
                    execution_id=tool_part.id,
                    state=state,
                )
            
        finally:
            if tool_call_id in self.active_calls:
                del self.active_calls[tool_call_id]
        
        return tool_part
    
    async def check_doom_loop(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        last_three_inputs: List[Dict[str, Any]]
    ) -> bool:
        """Detect infinite loops (3 consecutive identical tool calls)"""
        if not last_three_inputs:
            return False
        
        current_input = tool_input
        for prev_input in last_three_inputs:
            if prev_input == current_input:
                logger.warning(f"Potential doom loop detected: {tool_name}")
                return True
        
        return False
    
    def cleanup(self):
        """Cancel all active tool calls"""
        for call_id, context in list(self.active_calls.items()):
            context.abort.set()
            logger.info(f"Cleaning up tool call {call_id}")


def create_tool_manager(
    session_id: str,
    tool_registry: Optional[ToolRegistry] = None,
    session_lifecycle: Optional[Any] = None,
    tracker: Optional[ToolExecutionTracker] = None,
) -> ToolExecutionManager:
    """Factory function to create tool manager"""
    return ToolExecutionManager(session_id, tool_registry, session_lifecycle, tracker)
