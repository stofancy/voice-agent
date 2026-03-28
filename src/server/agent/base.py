"""
Base agent interface for Voice Agent.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any


class AgentEvent:
    """Base class for agent events."""
    
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
    
    def __repr__(self) -> str:
        return f"AgentEvent(type={self.event_type}, data={self.data})"


class ToolEvent(AgentEvent):
    """Tool-related event."""
    
    def __init__(self, tool_name: str, status: str, data: Dict[str, Any]):
        super().__init__("tool", {"tool": tool_name, "status": status, **data})
        self.tool_name = tool_name
        self.status = status


class BaseAgent(ABC):
    """
    Abstract base class for specialized agents.
    
    All agents (BookingAgent, QueryAgent, etc.) must implement this interface.
    """
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        pass
    
    @abstractmethod
    async def astream(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream agent response events.
        
        Args:
            input_text: User input text
            conversation_history: Optional conversation history
            
        Yields:
            AgentEvent instances representing the response
        """
        pass
    
    @abstractmethod
    async def ainvoke(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """
        Invoke agent and return complete response.
        
        Args:
            input_text: User input text
            conversation_history: Optional conversation history
            
        Returns:
            Complete text response from agent
        """
        pass
