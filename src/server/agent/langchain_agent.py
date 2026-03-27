"""
LangChain Agent wrapper for Voice Agent.

Wraps LangChain agent with astream_events() for non-blocking tool execution.
"""

import asyncio
from collections import deque
from typing import AsyncGenerator, Dict, List, Any, Optional

from loguru import logger

from .base import BaseAgent, AgentEvent
from .events import StreamChunkEvent, ToolStartEvent, ToolCompleteEvent, ToolErrorEvent, ToolProgressEvent


TOOL_PROGRESS_MESSAGES = {
    "search_hotels": "Searching for hotels...",
    "book_hotel": "Processing your booking...",
    "get_weather": "Checking the weather...",
    "echo": "Processing...",
    "default": "One moment please...",
}

TOOL_TIMEOUT_SECONDS = 30.0
TOOL_PROGRESS_INTERVAL_SECONDS = 0.5
BACKPRESSURE_MAX_DEPTH = 100

FALLBACK_TIMEOUT_MESSAGE = "Sorry, the request timed out. Would you like me to try again?"
FALLBACK_ERROR_MESSAGE = "Sorry, something went wrong. Please try again."


class BackpressureQueue:
    """
    Queue with backpressure support.

    When max_depth is reached, dropping the oldest item to make room.
    """

    def __init__(self, max_depth: int = BACKPRESSURE_MAX_DEPTH):
        self._queue: deque[AgentEvent] = deque(maxlen=max_depth)
        self._max_depth = max_depth

    def put_nowait(self, event: AgentEvent) -> None:
        """Put an event in the queue, dropping oldest if full."""
        if len(self._queue) >= self._max_depth:
            dropped = self._queue.popleft()
            logger.warning(
                f"Backpressure: queue full (max={self._max_depth}), dropping oldest event: {type(dropped).__name__}"
            )
        self._queue.append(event)

    def get_nowait(self) -> AgentEvent:
        """Get an event from the queue."""
        return self._queue.popleft()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0


class LangChainAgent(BaseAgent):
    """
    LangChain agent wrapper with streaming support.

    Uses astream_events() to emit tool events without blocking the stream.
    """

    def __init__(
        self,
        agent_type: str,
        llm: Any,
        tools: List[Any],
        stream_controller=None,
        system_prompt: Optional[str] = None,
        agent_executor: Any = None,
        tool_timeout: float = TOOL_TIMEOUT_SECONDS,
    ):
        """
        Initialize LangChainAgent.

        Args:
            agent_type: Type identifier for this agent
            llm: LangChain LLM (ChatOpenAI) - used if agent_executor not provided
            tools: List of LangChain tools - used if agent_executor not provided
            stream_controller: Optional StreamController for TTS
            system_prompt: Optional system prompt - used if agent_executor not provided
            agent_executor: Pre-created LangChain AgentExecutor (takes precedence)
            tool_timeout: Timeout for tool execution in seconds (default 30s)
        """
        self._agent_type = agent_type
        self._llm = llm
        self._tools = tools
        self._stream_controller = stream_controller
        self._system_prompt = system_prompt or "You are a helpful voice assistant."
        self._conversation_history: List[Dict[str, str]] = []
        self._agent_executor = agent_executor
        self._tool_timeout = tool_timeout

    @property
    def agent_type(self) -> str:
        return self._agent_type

    @property
    def has_agent_executor(self) -> bool:
        """Check if agent executor is available."""
        return self._agent_executor is not None

    def _get_progress_message(self, tool_name: str) -> str:
        """Get appropriate progress message for tool."""
        if tool_name in TOOL_PROGRESS_MESSAGES:
            return TOOL_PROGRESS_MESSAGES[tool_name]
        return TOOL_PROGRESS_MESSAGES["default"]

    async def _emit_periodic_progress(
        self,
        tool_name: str,
        stop_event: asyncio.Event,
        event_queue: BackpressureQueue,
    ) -> None:
        """Background task that emits progress every 500ms while tool runs."""
        try:
            while not stop_event.is_set():
                await asyncio.sleep(TOOL_PROGRESS_INTERVAL_SECONDS)
                if self._stream_controller and not stop_event.is_set():
                    await self._stream_controller.emit_progress(
                        self._get_progress_message(tool_name)
                    )
                # Also put progress event in queue for stream consumers
                if not stop_event.is_set():
                    event_queue.put_nowait(
                        ToolProgressEvent(tool_name=tool_name, status="progress")
                    )
        except asyncio.CancelledError:
            pass

    async def astream(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream agent response with tool events.

        Uses LangChain's astream_events for non-blocking tool execution.
        Emits TTS text via stream_controller for continuous audio.
        """
        # Track whether we created a new history list (vs using provided one)
        using_provided_history = conversation_history is not None
        messages = conversation_history if using_provided_history else self._conversation_history
        if not using_provided_history:
            messages.append({"role": "user", "content": input_text})

        # Event queue with backpressure support (max_depth=100)
        event_queue: BackpressureQueue = BackpressureQueue(max_depth=BACKPRESSURE_MAX_DEPTH)
        tool_stop_event: Optional[asyncio.Event] = None
        progress_task: Optional[asyncio.Task] = None
        timeout_task: Optional[asyncio.Task] = None
        current_tool_name: Optional[str] = None

        async def emit_timeout():
            """Background task that fires on tool timeout."""
            try:
                await asyncio.sleep(self._tool_timeout)
                # Timeout fired - tool is still running
                if self._stream_controller:
                    await self._stream_controller.emit_progress(FALLBACK_TIMEOUT_MESSAGE)
                event_queue.put_nowait(
                    ToolErrorEvent(tool_name=current_tool_name or "unknown", error="timeout")
                )
            except asyncio.CancelledError:
                pass

        try:
            if self._agent_executor is not None:
                # Use pre-created agent executor
                async for event in self._agent_executor.astream_events(
                    {"input": input_text, "chat_history": messages}
                ):
                    event_type = event.get("event")

                    if event_type == "on_llm_stream":
                        token = event.get("data", {}).get("chunk", {}).get("content", "")
                        if token:
                            yield StreamChunkEvent(text=token)

                    elif event_type == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        current_tool_name = tool_name
                        yield ToolStartEvent(tool_name=tool_name, tool_input=event.get("data", {}))

                        # Start periodic progress emission
                        tool_stop_event = asyncio.Event()
                        progress_task = asyncio.create_task(
                            self._emit_periodic_progress(tool_name, tool_stop_event, event_queue)
                        )
                        # Start timeout handler
                        timeout_task = asyncio.create_task(emit_timeout())
                        # Emit initial progress
                        if self._stream_controller:
                            await self._stream_controller.emit_progress(
                                self._get_progress_message(tool_name)
                            )

                    elif event_type == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        output = event.get("data", {}).get("output", {})

                        # Cancel progress and timeout tasks
                        if progress_task:
                            progress_task.cancel()
                            progress_task = None
                        if timeout_task:
                            timeout_task.cancel()
                            timeout_task = None
                        if tool_stop_event:
                            tool_stop_event.set()
                            tool_stop_event = None

                        current_tool_name = None

                        yield ToolCompleteEvent(tool_name=tool_name, tool_output=output)

                    # Check event queue for timeout/progress events
                    while not event_queue.empty():
                        yield event_queue.get_nowait()

            else:
                # Fallback: use LLM directly (legacy path)
                async for event in self._llm.astream_events({"messages": messages}):
                    event_type = event.get("event")

                    if event_type == "on_llm_stream":
                        token = event.get("data", {}).get("chunk", {}).get("content", "")
                        if token:
                            yield StreamChunkEvent(text=token)

                    elif event_type == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        current_tool_name = tool_name
                        yield ToolStartEvent(tool_name=tool_name, tool_input=event.get("data", {}))

                        # Start periodic progress emission
                        tool_stop_event = asyncio.Event()
                        progress_task = asyncio.create_task(
                            self._emit_periodic_progress(tool_name, tool_stop_event, event_queue)
                        )
                        # Start timeout handler
                        timeout_task = asyncio.create_task(emit_timeout())
                        # Emit initial progress
                        if self._stream_controller:
                            await self._stream_controller.emit_progress(
                                self._get_progress_message(tool_name)
                            )

                    elif event_type == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        output = event.get("data", {}).get("output", {})

                        # Cancel progress and timeout tasks
                        if progress_task:
                            progress_task.cancel()
                            progress_task = None
                        if timeout_task:
                            timeout_task.cancel()
                            timeout_task = None
                        if tool_stop_event:
                            tool_stop_event.set()
                            tool_stop_event = None

                        current_tool_name = None

                        yield ToolCompleteEvent(tool_name=tool_name, tool_output=output)

                    # Check event queue for timeout/progress events
                    while not event_queue.empty():
                        yield event_queue.get_nowait()

        except asyncio.TimeoutError:
            # Handle timeout during LLM streaming (less common)
            if self._stream_controller:
                await self._stream_controller.emit_progress(FALLBACK_TIMEOUT_MESSAGE)
            yield ToolErrorEvent(tool_name=current_tool_name or "unknown", error="timeout")
        finally:
            # Cleanup tasks
            if progress_task:
                progress_task.cancel()
            if timeout_task:
                timeout_task.cancel()
            if tool_stop_event:
                tool_stop_event.set()
            # Only append to instance history if we created it locally
            if not using_provided_history:
                self._conversation_history.append({"role": "user", "content": input_text})

    async def ainvoke(
        self,
        input_text: str,
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """Invoke agent and return complete response."""
        messages = conversation_history or self._conversation_history
        messages.append({"role": "user", "content": input_text})

        response = ""
        async for event in self.astream(input_text, messages):
            if isinstance(event, StreamChunkEvent):
                response += event.text

        self._conversation_history.append({"role": "assistant", "content": response})
        return response
