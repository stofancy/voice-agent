"""
Base classes for booking stage tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loguru import logger


class StageAction(str, Enum):
    """Action to take after stage completes."""

    CONTINUE = "continue"  # Auto-proceed to next stage
    WAIT_FOR_SELECTION = "wait_for_selection"  # Wait for user to select option
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"  # Wait for user to confirm
    COMPLETE = "complete"  # Booking complete
    ERROR = "error"  # Stage failed


@dataclass
class StageResult:
    """
    Result from a stage tool execution.

    Attributes:
        stage: Current stage name
        data: Structured data extracted (hotels, rooms, etc.)
        action: Action to take next
        message: Human-readable message for the user
        options: List of options for user to select (if WAIT_FOR_SELECTION)
        error: Error message if action is ERROR
    """

    stage: str
    data: dict[str, Any] = field(default_factory=dict)
    action: StageAction = StageAction.CONTINUE
    message: str = ""
    options: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "stage": self.stage,
            "data": self.data,
            "action": self.action.value,
            "message": self.message,
        }
        if self.options:
            result["options"] = self.options
        if self.error:
            result["error"] = self.error
        return result


class BookingStage(ABC):
    """
    Base class for a booking stage tool.

    Each stage performs a specific step in the hotel booking flow.
    """

    def __init__(self, name: str, stage_index: int):
        """
        Initialize stage.

        Args:
            name: Stage name (e.g., "search", "select_hotel")
            stage_index: Index in the booking flow (0-6)
        """
        self.name = name
        self.stage_index = stage_index

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this stage does."""
        pass

    @abstractmethod
    async def execute(
        self,
        browser_controller: Any,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Execute the stage.

        Args:
            browser_controller: BrowserController instance
            context: Booking context with user input, previous results, etc.

        Returns:
            StageResult with data and next action
        """
        pass

    def should_skip(self, context: dict[str, Any]) -> bool:
        """
        Check if this stage should be skipped based on context.

        Args:
            context: Booking context

        Returns:
            True if stage should be skipped
        """
        # Skip if we have required data already (e.g., user provided dates upfront)
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, index={self.stage_index})"


class TurnContext:
    """
    Context for the current booking turn.

    Maintains state across stages within a single booking session.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_stage_index: int = 0
        self.booking_data: dict[str, Any] = {}
        self.user_inputs: list[str] = []
        self.errors: list[str] = []
        self.selected_items: dict[str, Any] = {}

    def update(self, **kwargs) -> None:
        """Update context with new data."""
        self.booking_data.update(kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context."""
        return self.booking_data.get(key, default)

    def set_selected(self, category: str, item: dict) -> None:
        """Record a user selection."""
        self.selected_items[category] = item

    def get_selected(self, category: str) -> dict | None:
        """Get a user selection."""
        return self.selected_items.get(category)

    def advance_stage(self) -> None:
        """Move to next stage."""
        self.current_stage_index += 1

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
        logger.warning(f"[TurnContext] Error: {error}")

    def add_user_input(self, text: str) -> None:
        """Record user input."""
        self.user_inputs.append(text)
