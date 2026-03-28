# Contract: BookingStage

**Type**: Abstract Base Class
**Module**: `src.server.browser.stages.base`
**Status**: Required

## Interface

```python
from abc import ABC, abstractmethod

class BookingStage(ABC):
    def __init__(self, name: str, stage_index: int) -> None:
        """
        Initialize stage.

        Args:
            name: Stage identifier (e.g., "search", "select_hotel")
            stage_index: Position in booking flow (0-6)
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of stage purpose."""

    @abstractmethod
    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Execute the stage.

        Args:
            browser_controller: BrowserController instance
            context: Booking context with user input, previous results

        Returns:
            StageResult with data and next action
        """

    def should_skip(self, context: dict[str, Any]) -> bool:
        """
        Check if stage should be skipped.

        Returns:
            True if stage is redundant given context
        """
```

## Stage Registry

| Stage | Class | Index | Action |
|-------|-------|-------|--------|
| search | BookHotelSearchTool | 0 | CONTINUE |
| select_hotel | BookHotelSelectHotelTool | 1 | WAIT_FOR_SELECTION |
| navigate_property | BookHotelNavigatePropertyTool | 2 | CONTINUE |
| select_room | BookHotelSelectRoomTool | 3 | WAIT_FOR_SELECTION |
| confirm_selection | BookHotelConfirmSelectionTool | 4 | WAIT_FOR_CONFIRMATION |
| fill_guest | BookHotelFillGuestTool | 5 | CONTINUE |
| finalize | BookHotelFinalizeTool | 6 | COMPLETE |

## Context Schema

```python
{
    "location": str,           # Search destination
    "checkin": str,           # YYYY-MM-DD
    "checkout": str,          # YYYY-MM-DD
    "guests": int,            # 1-10
    "rooms": int,             # 1-5
    "selected_hotel": HotelOption,
    "selected_room": RoomOption,
    "guest_name": str,
    "guest_email": str,
    "search_url": str,        # Set after search
    "property_url": str,      # Set after navigation
}
```

## StageResult Schema

```python
{
    "stage": str,                    # Stage name
    "action": StageAction,          # CONTINUE | WAIT_FOR_SELECTION | etc.
    "data": dict,                   # Stage-specific payload
    "message": str,                 # User-facing message
    "options": [                    # Only if action is WAIT_FOR_SELECTION
        {
            "index": int,
            "id": str,
            "name": str,
            "display": str,
            "details": dict
        }
    ],
    "error": str | None            # Only if action is ERROR
}
```
