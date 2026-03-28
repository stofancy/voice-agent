"""
Voice Booking Agent - LLM-based booking orchestration with Stage Tools.

Handles natural language understanding and orchestrates Stage Tools
for the complete hotel booking flow.
"""

import json
from typing import Any, Dict, List, Optional, AsyncGenerator

from loguru import logger

from .base import AgentEvent
from .events import AgentStartEvent, AgentCompleteEvent
from .langchain_agent import LangChainAgent
from .tools.stage_tool_wrapper import (
    get_all_langchain_tools,
    StageToolWrapper,
    ToolResult,
)
from src.server.browser.stages.base import StageAction


# System prompt for booking agent - instructs LLM how to interpret NL and call tools
BOOKING_SYSTEM_PROMPT = """You are a voice booking assistant specialized in hotel booking on Booking.com.

## Your Capabilities
You can help users:
1. Search for hotels by location, dates, and guest count
2. Select hotels and rooms using natural language
3. Fill guest information
4. Complete booking and reach payment page

## How to Interpret User Selection

When user says natural language like "第二个", "贵一点的", etc:

| User Input | Interpretation | Action |
|------------|---------------|--------|
| "第一个" / "第一个酒店" | index=1 | Select hotel at index 1 |
| "第二个" / "第二个酒店" | index=2 | Select hotel at index 2 |
| "第三个" | index=3 | Select hotel at index 3 |
| "贵一点的" | preference=price_desc | Sort by price descending, pick first |
| "便宜点的" | preference=price_asc | Sort by price ascending, pick first |
| "评分最高的" | preference=rating_desc | Sort by rating descending, pick first |
| "带早餐的" | preference=breakfast | Filter hotels with breakfast included |

## Stage Flow

When user wants to book a hotel, you orchestrate these tools in sequence:

1. **search_hotels** - Search for hotels by location
   - Required: location
   - Optional: checkin, checkout, guests, rooms

2. **select_hotel** - Select from search results
   - User can specify by index (1, 2, 3...) or by preference (贵一点的, 评分最高的)
   - Returns WAIT_FOR_SELECTION with hotel options

3. **navigate_to_hotel** - Navigate to hotel property page
   - Required: hotel_url

4. **select_room** - Select room type
   - User can specify by index or preference
   - Returns WAIT_FOR_SELECTION with room options

5. **confirm_selection** - Confirm booking details
   - Returns WAIT_FOR_CONFIRMATION with summary

6. **fill_guest_info** - Fill guest name and email
   - Required: guest_name
   - Optional: guest_email, guest_phone

7. **finalize_booking** - Complete booking
   - Returns COMPLETE when payment page reached

## Important Rules

1. ALWAYS search first before trying to select a hotel
2. When you receive WAIT_FOR_SELECTION, present options to user and ask for selection
3. When you receive WAIT_FOR_CONFIRMATION, show summary and ask for confirmation
4. NEVER ask for credit card or payment information
5. After finalize_booking, tell user to complete payment manually
6. If any step fails, inform user and suggest alternatives

## Output Format

When presenting options, use this format:
- For hotel options:
  "找到 {count} 家酒店:
  1. {name} - {price} - 评分: {rating}
  2. {name} - {price} - 评分: {rating}"

- For room options:
  "找到 {count} 种房型:
  1. {name} - {price} - 最多 {max_guests} 人
  2. {name} - {price} - 最多 {max_guests} 人"

- For confirmation:
  "预订摘要:
  酒店: {hotel_name}
  房型: {room_name}
  入住: {checkin}
  退房: {checkout}
  人数: {guests}
  价格: {price}

  确认预订吗？"
"""


class BookingState:
    """Tracks the current state of a booking session."""

    STAGE_NAMES = [
        "search",
        "select_hotel",
        "navigate_property",
        "select_room",
        "confirm_selection",
        "fill_guest",
        "finalize",
    ]

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_stage_index = 0
        self.context: Dict[str, Any] = {}
        self.selected_options: Dict[str, Any] = {}
        self.completed_stages: List[str] = []

    @property
    def current_stage(self) -> str:
        return self.STAGE_NAMES[self.current_stage_index]

    @property
    def is_complete(self) -> bool:
        return self.current_stage_index >= len(self.STAGE_NAMES)


class VoiceBookingAgent:
    """
    Voice-controlled booking agent with Stage Tool orchestration.

    Uses LLM for natural language understanding and orchestrates
    Stage Tools for browser automation.
    """

    def __init__(
        self,
        llm: Any,
        browser_controller: Any = None,
        stream_controller: Any = None,
    ):
        """
        Initialize VoiceBookingAgent.

        Args:
            llm: LangChain LLM (ChatOpenAI)
            browser_controller: BrowserController for browser automation
            stream_controller: Optional StreamController for TTS
        """
        self._llm = llm
        self._browser_controller = browser_controller
        self._stream_controller = stream_controller
        self._session_states: Dict[str, BookingState] = {}

        # Get LangChain tools
        self._tools = get_all_langchain_tools()
        self._tool_map = {tool.name: tool for tool in self._tools}
        self._tool_wrappers: Dict[str, StageToolWrapper] = {}

        # Initialize tool wrappers map
        from .tools.stage_tool_wrapper import get_all_stage_wrappers
        for wrapper in get_all_stage_wrappers():
            self._tool_wrappers[wrapper.name] = wrapper

        # Create LangChain agent
        self._agent = LangChainAgent(
            agent_type="voice_booking",
            llm=llm,
            tools=self._tools,
            stream_controller=stream_controller,
            system_prompt=BOOKING_SYSTEM_PROMPT,
        )

    def _get_or_create_state(self, session_id: str) -> BookingState:
        """Get or create booking state for session."""
        if session_id not in self._session_states:
            self._session_states[session_id] = BookingState(session_id)
        return self._session_states[session_id]

    def _apply_preference(
        self,
        options: List[Dict[str, Any]],
        preference: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Apply user preference to select from options.

        Args:
            options: List of option dicts
            preference: Preference string (price_desc, rating_desc, etc.)

        Returns:
            Selected option or None
        """
        if not options or not preference:
            return None

        preference = preference.lower()

        if preference == "price_desc":
            # Sort by price descending
            valid = [o for o in options if o.get("details", {}).get("price")]
            if valid:
                return max(valid, key=lambda x: self._parse_price(x.get("details", {}).get("price", "0")))
        elif preference == "price_asc":
            valid = [o for o in options if o.get("details", {}).get("price")]
            if valid:
                return min(valid, key=lambda x: self._parse_price(x.get("details", {}).get("price", "999999")))
        elif preference == "rating_desc":
            valid = [o for o in options if o.get("details", {}).get("score")]
            if valid:
                return max(valid, key=lambda x: float(x.get("details", {}).get("score", "0")))

        return None

    def _parse_price(self, price_str: str) -> float:
        """Parse price string to float."""
        if not price_str:
            return 0.0
        # Remove non-numeric chars except . and ,
        import re
        numbers = re.findall(r"[\d,.]+", str(price_str))
        if numbers:
            return float(numbers[0].replace(",", ""))
        return 0.0

    def _select_by_index(
        self,
        options: List[Dict[str, Any]],
        index: int,
    ) -> Optional[Dict[str, Any]]:
        """Select option by 1-based index."""
        if 1 <= index <= len(options):
            return options[index - 1]
        return None

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        session_id: str,
    ) -> ToolResult:
        """
        Execute a stage tool and return result.

        Args:
            tool_name: Name of tool to execute
            tool_args: Tool arguments
            session_id: Session ID for state tracking

        Returns:
            ToolResult from stage execution
        """
        state = self._get_or_create_state(session_id)

        logger.info(f"[VoiceBookingAgent] Executing {tool_name} for session {session_id}")

        # Get wrapper and execute
        wrapper = self._tool_wrappers.get(tool_name)
        if not wrapper:
            return ToolResult(
                success=False,
                data={},
                message="",
                action="error",
                error=f"Unknown tool: {tool_name}",
            )

        result = await wrapper.execute(tool_args, self._browser_controller)

        # Update state based on result
        if result.success:
            state.context.update(result.data)
            if result.action == StageAction.CONTINUE.value:
                state.completed_stages.append(tool_name)
            elif result.action == StageAction.WAIT_FOR_SELECTION.value:
                # Store options for later selection
                state.selected_options[tool_name] = result.options

        return result

    # Mapping from stage name to tool name
    STAGE_TO_TOOL = {
        "search": "search_hotels",
        "select_hotel": "select_hotel",
        "navigate_property": "navigate_to_hotel",
        "select_room": "select_room",
        "confirm_selection": "confirm_selection",
        "fill_guest": "fill_guest_info",
        "finalize": "finalize_booking",
    }

    async def _handle_selection(
        self,
        user_input: str,
        session_id: str,
    ) -> ToolResult:
        """
        Handle user selection from WAIT_FOR_SELECTION state.

        Parses NL selection (第二个, 贵一点的) and executes selection.
        """
        state = self._get_or_create_state(session_id)

        # Determine which tool's options to select from
        current_tool = self.STAGE_TO_TOOL.get(state.current_stage, state.current_stage)
        options = state.selected_options.get(current_tool, [])

        if not options:
            return ToolResult(
                success=False,
                data={},
                message="No options available for selection",
                action="error",
                error="No options to select from",
            )

        # Parse user input
        user_lower = user_input.lower().strip()

        # Try index selection
        index_map = {"第一": 1, "第二": 2, "第三": 3, "第四": 4, "第五": 5}
        for chinese, idx in index_map.items():
            if chinese in user_lower or str(idx) in user_lower:
                selected = self._select_by_index(options, idx)
                if selected:
                    return ToolResult(
                        success=True,
                        data={"selected": selected},
                        message=f"Selected: {selected.get('name')}",
                        action=StageAction.CONTINUE.value,
                        options=options,
                    )

        # Try preference selection
        if "贵" in user_lower:
            selected = self._apply_preference(options, "price_desc")
        elif "便宜" in user_lower:
            selected = self._apply_preference(options, "price_asc")
        elif "评分" in user_lower or "好" in user_lower:
            selected = self._apply_preference(options, "rating_desc")
        elif "早餐" in user_lower:
            # Filter for breakfast - simplified
            selected = options[0] if options else None
        else:
            selected = None

        if selected:
            return ToolResult(
                success=True,
                data={"selected": selected},
                message=f"Selected: {selected.get('name')}",
                action=StageAction.CONTINUE.value,
                options=options,
            )

        return ToolResult(
            success=False,
            data={},
            message=f"Could not understand selection. Available: {len(options)} options",
            action=StageAction.WAIT_FOR_SELECTION.value,
            options=options,
            error="Invalid selection",
        )

    async def astream(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream agent response.

        Args:
            user_input: User's voice input (transcribed)
            session_id: Session ID for state tracking

        Yields:
            AgentEvent for each step
        """
        yield AgentStartEvent(agent_type="voice_booking", input_text=user_input)

        state = self._get_or_create_state(session_id)

        # Check if we're in a selection state
        if state.selected_options.get(state.current_stage):
            # Handle selection
            result = await self._handle_selection(user_input, session_id)
            yield ToolCompleteEvent(tool_name="select", tool_output=result.to_dict())
        else:
            # Use LLM agent for general booking flow
            async for event in self._agent.astream(user_input, turn_id=session_id):
                yield event

        yield AgentCompleteEvent(agent_type="voice_booking", full_response="")

    async def ainvoke(
        self,
        user_input: str,
        session_id: str = "default",
    ) -> str:
        """
        Invoke agent and return complete response.

        Args:
            user_input: User's voice input
            session_id: Session ID

        Returns:
            Agent's complete response
        """
        response = ""
        async for event in self.astream(user_input, session_id):
            if isinstance(event, AgentEvent):
                if hasattr(event, "text"):
                    response += event.text
        return response

    async def execute_stage(
        self,
        stage_name: str,
        tool_args: Dict[str, Any],
        session_id: str = "default",
    ) -> ToolResult:
        """
        Directly execute a stage tool (bypasses LLM).

        Useful for testing or when LLM has already determined the action.

        Args:
            stage_name: Name of stage tool to execute
            tool_args: Tool arguments
            session_id: Session ID

        Returns:
            ToolResult from stage execution
        """
        return await self._execute_tool(stage_name, tool_args, session_id)

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current booking state for session."""
        state = self._session_states.get(session_id)
        if not state:
            return None

        return {
            "session_id": state.session_id,
            "current_stage": state.current_stage,
            "current_stage_index": state.current_stage_index,
            "context": state.context,
            "completed_stages": state.completed_stages,
            "is_complete": state.is_complete,
        }

    def reset_session(self, session_id: str) -> None:
        """Reset booking state for session."""
        if session_id in self._session_states:
            del self._session_states[session_id]
