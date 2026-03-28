"""
Stage Tool Wrapper for LangChain integration.

Wraps BookingStage tools as LangChain StructuredTools, converting between
LangChain tool arguments and BookingStage context dict.
"""

import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.callbacks import CallbackManagerForToolRun

from loguru import logger

from src.server.browser.stages.base import BookingStage, StageResult, StageAction


@dataclass
class ToolResult:
    """Result from StageTool execution."""
    success: bool
    data: Dict[str, Any]
    message: str
    action: str
    options: List[Dict] = None
    error: str = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "data": self.data,
        }
        if self.options:
            result["options"] = self.options
        if self.error:
            result["error"] = self.error
        return result


class StageToolWrapper:
    """
    Wraps a BookingStage as a LangChain StructuredTool.

    Converts between LangChain tool arguments (individual params) and
    BookingStage context dict (all booking data).

    Example:
        wrapper = StageToolWrapper(
            stage=BookHotelSearchTool(),
            name="search_hotels",
            description="Search for hotels on Booking.com"
        )
        tool = wrapper.to_langchain_tool()
    """

    def __init__(
        self,
        stage: BookingStage,
        name: str,
        description: str,
        # Schema defines the tool's input schema
        input_schema: Dict[str, Any] = None,
        # Function to convert tool args to context dict
        args_to_context: Callable[[Dict[str, Any]], Dict[str, Any]] = None,
        # Function to convert context to tool result
        context_to_result: Callable[[Dict[str, Any], StageResult], ToolResult] = None,
    ):
        """
        Initialize StageToolWrapper.

        Args:
            stage: BookingStage instance to wrap
            name: Tool name for LangChain
            description: Tool description for LLM
            input_schema: JSON schema for tool input (defaults to context keys)
            args_to_context: Optional converter from tool args to context dict.
                            If not provided, tool args are passed as context dict.
            context_to_result: Optional converter from StageResult to ToolResult.
                              If not provided, uses default conversion.
        """
        self.stage = stage
        self.name = name
        self.description = description
        self.input_schema = input_schema or {}
        self.args_to_context = args_to_context or self._default_args_to_context
        self.context_to_result = context_to_result or self._default_context_to_result

    def _default_args_to_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Default: pass tool args directly as context dict."""
        return args

    def _default_context_to_result(
        self,
        context: Dict[str, Any],
        stage_result: StageResult
    ) -> ToolResult:
        """Default conversion from StageResult to ToolResult."""
        return ToolResult(
            success=stage_result.action != StageAction.ERROR,
            data=stage_result.data,
            message=stage_result.message,
            action=stage_result.action.value,
            options=stage_result.options if hasattr(stage_result, 'options') else [],
            error=stage_result.error,
        )

    async def execute(
        self,
        args: Dict[str, Any],
        browser_controller: Any = None,
    ) -> ToolResult:
        """
        Execute the wrapped stage with given arguments.

        Args:
            args: Tool arguments from LangChain
            browser_controller: BrowserController instance for browser operations

        Returns:
            ToolResult with execution outcome
        """
        # Convert tool args to context dict
        context = self.args_to_context(args)

        logger.info(f"[StageToolWrapper] Executing {self.stage.name} with context: {list(context.keys())}")

        try:
            # Execute the stage
            stage_result = await self.stage.execute(browser_controller, context)

            # Convert result
            return self.context_to_result(context, stage_result)

        except Exception as e:
            logger.error(f"[StageToolWrapper] {self.stage.name} failed: {e}")
            return ToolResult(
                success=False,
                data={},
                message="",
                action="error",
                error=str(e),
            )

    async def ainvoke(
        self,
        tool_input: Dict[str, Any],
        browser_controller: Any = None,
    ) -> Dict[str, Any]:
        """
        LangChain-style async invoke.

        Args:
            tool_input: Tool input dict from LangChain
            browser_controller: BrowserController instance

        Returns:
            Tool output as dict
        """
        result = await self.execute(tool_input, browser_controller)
        return result.to_dict()

    def to_langchain_tool(self) -> StructuredTool:
        """
        Convert to LangChain StructuredTool.

        Returns:
            StructuredTool instance ready for LangChain agent
        """
        async def _ainvoke(
            tool_input: Dict[str, Any],
            browser_controller: Any = None,
        ) -> str:
            """Async invoke wrapper for LangChain."""
            result = await self.execute(tool_input, browser_controller)
            return json.dumps(result.to_dict(), ensure_ascii=False)

        # Build description from schema
        param_descriptions = []
        for param_name, param_info in self.input_schema.get("properties", {}).items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            param_descriptions.append(f"{param_name} ({param_type}): {param_desc}")

        full_description = f"{self.description}\n\nParameters:\n" + "\n".join(param_descriptions) if param_descriptions else self.description

        return StructuredTool(
            name=self.name,
            description=full_description,
            args_schema=self.input_schema,
            ainvoke=_ainvoke,
        )


# Pre-built wrappers for each booking stage

def create_search_tool_wrapper(browser_controller_getter: Callable = None) -> StageToolWrapper:
    """Create wrapper for BookHotelSearchTool."""
    from src.server.browser.stages.search import BookHotelSearchTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "location": args.get("location"),
            "checkin": args.get("checkin"),
            "checkout": args.get("checkout"),
            "guests": args.get("guests", 1),
            "rooms": args.get("rooms", 1),
        }

    return StageToolWrapper(
        stage=BookHotelSearchTool(),
        name="search_hotels",
        description="Search for hotels on Booking.com. Returns list of hotels with prices.",
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or area to search"},
                "checkin": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                "checkout": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                "guests": {"type": "integer", "description": "Number of guests", "default": 1},
                "rooms": {"type": "integer", "description": "Number of rooms", "default": 1},
            },
            "required": ["location"],
        },
        args_to_context=args_to_context,
    )


def create_select_hotel_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelSelectHotelTool."""
    from src.server.browser.stages.select_hotel import BookHotelSelectHotelTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "selected_hotel_index": args.get("selected_index"),
            "selected_hotel_id": args.get("selected_id"),
            "preference": args.get("preference"),  # e.g., "price_desc", "rating_desc"
        }

    def context_to_result(context: Dict[str, Any], stage_result: StageResult) -> ToolResult:
        return ToolResult(
            success=stage_result.action != StageAction.ERROR,
            data=stage_result.data,
            message=stage_result.message,
            action=stage_result.action.value,
            options=stage_result.options,
            error=stage_result.error,
        )

    return StageToolWrapper(
        stage=BookHotelSelectHotelTool(),
        name="select_hotel",
        description="Select a hotel from search results. Returns WAIT_FOR_SELECTION with hotel options.",
        input_schema={
            "type": "object",
            "properties": {
                "selected_index": {"type": "integer", "description": "Index of hotel to select (1-based)"},
                "selected_id": {"type": "string", "description": "ID of hotel to select"},
                "preference": {"type": "string", "description": "Selection preference: price_desc, rating_desc, etc."},
            },
        },
        args_to_context=args_to_context,
        context_to_result=context_to_result,
    )


def create_navigate_property_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelNavigatePropertyTool."""
    from src.server.browser.stages.navigate_property import BookHotelNavigatePropertyTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "selected_hotel": {
                "name": args.get("hotel_name"),
                "url": args.get("hotel_url"),
            }
        }

    return StageToolWrapper(
        stage=BookHotelNavigatePropertyTool(),
        name="navigate_to_hotel",
        description="Navigate to selected hotel's property page.",
        input_schema={
            "type": "object",
            "properties": {
                "hotel_name": {"type": "string", "description": "Name of selected hotel"},
                "hotel_url": {"type": "string", "description": "URL of hotel property page"},
            },
            "required": ["hotel_url"],
        },
        args_to_context=args_to_context,
    )


def create_select_room_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelSelectRoomTool."""
    from src.server.browser.stages.select_room import BookHotelSelectRoomTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "selected_room_index": args.get("selected_index"),
            "selected_room_id": args.get("selected_id"),
        }

    def context_to_result(context: Dict[str, Any], stage_result: StageResult) -> ToolResult:
        return ToolResult(
            success=stage_result.action != StageAction.ERROR,
            data=stage_result.data,
            message=stage_result.message,
            action=stage_result.action.value,
            options=stage_result.options,
            error=stage_result.error,
        )

    return StageToolWrapper(
        stage=BookHotelSelectRoomTool(),
        name="select_room",
        description="Select a room type from hotel property page. Returns WAIT_FOR_SELECTION with room options.",
        input_schema={
            "type": "object",
            "properties": {
                "selected_index": {"type": "integer", "description": "Index of room to select (1-based)"},
                "selected_id": {"type": "string", "description": "ID of room to select"},
            },
        },
        args_to_context=args_to_context,
        context_to_result=context_to_result,
    )


def create_confirm_selection_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelConfirmSelectionTool."""
    from src.server.browser.stages.confirm_selection import BookHotelConfirmSelectionTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "confirmed": args.get("confirmed", True),
        }

    return StageToolWrapper(
        stage=BookHotelConfirmSelectionTool(),
        name="confirm_selection",
        description="Confirm the current hotel and room selection. Returns WAIT_FOR_CONFIRMATION with summary.",
        input_schema={
            "type": "object",
            "properties": {
                "confirmed": {"type": "boolean", "description": "Whether user confirmed the selection", "default": True},
            },
        },
        args_to_context=args_to_context,
    )


def create_fill_guest_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelFillGuestTool."""
    from src.server.browser.stages.fill_guest import BookHotelFillGuestTool

    def args_to_context(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "guest_name": args.get("guest_name"),
            "guest_email": args.get("guest_email"),
            "guest_phone": args.get("guest_phone"),
        }

    return StageToolWrapper(
        stage=BookHotelFillGuestTool(),
        name="fill_guest_info",
        description="Fill in guest information (name, email) for the booking.",
        input_schema={
            "type": "object",
            "properties": {
                "guest_name": {"type": "string", "description": "Guest full name"},
                "guest_email": {"type": "string", "description": "Guest email address"},
                "guest_phone": {"type": "string", "description": "Guest phone number (optional)"},
            },
            "required": ["guest_name"],
        },
        args_to_context=args_to_context,
    )


def create_finalize_tool_wrapper() -> StageToolWrapper:
    """Create wrapper for BookHotelFinalizeTool."""
    from src.server.browser.stages.finalize import BookHotelFinalizeTool

    return StageToolWrapper(
        stage=BookHotelFinalizeTool(),
        name="finalize_booking",
        description="Complete the booking and navigate to payment page. Returns COMPLETE when payment page reached.",
        input_schema={
            "type": "object",
            "properties": {},
        },
    )


def get_all_stage_wrappers() -> List[StageToolWrapper]:
    """Get all stage tool wrappers."""
    return [
        create_search_tool_wrapper(),
        create_select_hotel_tool_wrapper(),
        create_navigate_property_tool_wrapper(),
        create_select_room_tool_wrapper(),
        create_confirm_selection_tool_wrapper(),
        create_fill_guest_tool_wrapper(),
        create_finalize_tool_wrapper(),
    ]


def get_all_langchain_tools() -> List[StructuredTool]:
    """Get all stage tools as LangChain StructuredTools."""
    return [wrapper.to_langchain_tool() for wrapper in get_all_stage_wrappers()]
