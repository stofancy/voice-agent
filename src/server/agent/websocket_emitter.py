"""
Agent WebSocket integration for emitting tool events.

Handles emission of tool lifecycle events to WebSocket client.
"""

from typing import Callable, Optional

from .events import (
    AgentEvent,
    ToolStartEvent,
    ToolCompleteEvent,
    ToolErrorEvent,
    AgentStartEvent,
    AgentCompleteEvent,
)


class AgentWebSocketEmitter:
    """
    Emits agent events to WebSocket client.
    
    Used to notify the frontend about tool lifecycle events
    so the UI can display progress during tool execution.
    """
    
    def __init__(self, send_func: Optional[Callable] = None):
        """
        Args:
            send_func: Async function to send WebSocket messages
        """
        self._send_func = send_func
    
    async def emit(self, event: AgentEvent) -> None:
        """
        Emit an agent event to the WebSocket.
        
        Args:
            event: AgentEvent to emit
        """
        if not self._send_func:
            return
        
        if isinstance(event, AgentStartEvent):
            await self._send_func({
                "type": "agent_start",
                "agent_type": event.agent_type,
            })
        elif isinstance(event, AgentCompleteEvent):
            await self._send_func({
                "type": "agent_complete",
                "agent_type": event.agent_type,
                "response": event.full_response,
            })
        elif isinstance(event, ToolStartEvent):
            await self._send_func({
                "type": "tool_start",
                "tool": event.tool_name,
                "input": event.tool_input,
            })
        elif isinstance(event, ToolCompleteEvent):
            await self._send_func({
                "type": "tool_complete",
                "tool": event.tool_name,
                "output": event.tool_output,
            })
        elif isinstance(event, ToolErrorEvent):
            await self._send_func({
                "type": "tool_error",
                "tool": event.tool_name,
                "error": event.error,
            })
