"""
Browser booking stage tools.

Each stage corresponds to a step in the hotel booking flow on Booking.com.
"""

from .base import BookingStage, StageResult, StageAction, TurnContext
from .search import BookHotelSearchTool
from .select_hotel import BookHotelSelectHotelTool
from .navigate_property import BookHotelNavigatePropertyTool
from .select_room import BookHotelSelectRoomTool
from .confirm_selection import BookHotelConfirmSelectionTool
from .fill_guest import BookHotelFillGuestTool
from .finalize import BookHotelFinalizeTool

# All stage tools
STAGE_TOOLS = [
    BookHotelSearchTool(),
    BookHotelSelectHotelTool(),
    BookHotelNavigatePropertyTool(),
    BookHotelSelectRoomTool(),
    BookHotelConfirmSelectionTool(),
    BookHotelFillGuestTool(),
    BookHotelFinalizeTool(),
]

__all__ = [
    "BookingStage",
    "StageResult",
    "StageAction",
    "TurnContext",
    "BookHotelSearchTool",
    "BookHotelSelectHotelTool",
    "BookHotelNavigatePropertyTool",
    "BookHotelSelectRoomTool",
    "BookHotelConfirmSelectionTool",
    "BookHotelFillGuestTool",
    "BookHotelFinalizeTool",
    "STAGE_TOOLS",
]
