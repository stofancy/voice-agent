"""
Browser automation module for Voice Agent.

Provides Chrome DevTools MCP integration for Booking.com automation.
"""

from .browser_controller import BrowserController, BrowserControllerConfig
from .exceptions import (
    BrowserError,
    NavigationError,
    ElementNotFoundError,
    PopupBlockedError,
    ScreenshotError,
)
from .stages import (
    BookingStage,
    StageResult,
    StageAction,
    TurnContext,
    STAGE_TOOLS,
    BookHotelSearchTool,
    BookHotelSelectHotelTool,
    BookHotelNavigatePropertyTool,
    BookHotelSelectRoomTool,
    BookHotelConfirmSelectionTool,
    BookHotelFillGuestTool,
    BookHotelFinalizeTool,
)

__all__ = [
    # Controller
    "BrowserController",
    "BrowserControllerConfig",
    # Exceptions
    "BrowserError",
    "NavigationError",
    "ElementNotFoundError",
    "PopupBlockedError",
    "ScreenshotError",
    # Stages
    "BookingStage",
    "StageResult",
    "StageAction",
    "TurnContext",
    "STAGE_TOOLS",
    "BookHotelSearchTool",
    "BookHotelSelectHotelTool",
    "BookHotelNavigatePropertyTool",
    "BookHotelSelectRoomTool",
    "BookHotelConfirmSelectionTool",
    "BookHotelFillGuestTool",
    "BookHotelFinalizeTool",
]
