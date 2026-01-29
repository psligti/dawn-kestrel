"""
Tool execution framework with AI integration.

Handles tool calls from AI providers, coordinates execution,
manages permissions, and updates tool state.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from opencode_python.core.event_bus import bus, Events
from opencode_python.core.settings import settings
from opencode_python.tools.framework import Tool, ToolContext, ToolResult, ToolRegistry
from opencode_python.providers.base import StreamEvent, TokenUsage
from opencode_python.core.models import ToolState, ToolPart


logger = logging.getLogger(__name__)


class ToolExecutionManager:
    """Manages tool execution from AI responses"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_calls: Dict[str, ToolContext] = {}
        self.tool_registry = ToolRegistry()
    
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
        
        logger.info(f"Executing tool: {tool_name} with input: {tool_input.keys()}")
        
        tool_context = ToolContext(
            session_id=self.session_id,
            message_id=message_id,
            agent=agent,
            model=model,
            call_id=tool_call_id,
            abort=asyncio.Event(),
            messages=[],
            metadata=self._get_metadata,
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
        
        try:
            self.active_calls[tool_call_id] = tool_context
            
            result = await tool.execute(tool_input, tool_context)
            
            state.status = "completed"
            state.time_start = tool_context.time_created
            state.time_end = tool_context.time_finished
            state.output = result.output
            state.title = result.title
            state.metadata = result.metadata
            
            await bus.publish(Events.TOOL_COMPLETED, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "result": result.output,
                "title": result.title,
                "metadata": result.metadata
            })
            
        except asyncio.CancelledError:
            logger.warning(f"Tool {tool_name} cancelled by user")
            state.status = "error"
            state.error = "Cancelled by user"
            await bus.publish(Events.TOOL_ERROR, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "error": state.error
            })
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            state.status = "error"
            state.error = str(e)
            await bus.publish(Events.TOOL_ERROR, {
                "part_id": tool_part.id,
                "session_id": self.session_id,
                "tool": tool_name,
                "error": state.error
            })
            
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
            model=model,
            call_id=tool_call_id,
            abort=asyncio.Event(),
            messages=[],
            metadata=self._get_metadata,
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
        
        try:
            self.active_calls[tool_call_id] = tool_context
            
            result = await tool.execute(tool_input, tool_context)
            
            state.status = "completed"
            state.time_end = tool_context.time_finished
            state.output = result.output
            state.title = result.title
            state.metadata = result.metadata
            
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
            
        except Exception as e:
            logger.error(f"Tool {tool_name} stream failed: {e}")
            state.status = "error"
            state.error = str(e)
            
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


def create_tool_manager(session_id: str) -> ToolExecutionManager:
    """Factory function to create tool manager"""
    return ToolExecutionManager(session_id)
