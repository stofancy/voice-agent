"""
Stage 5: Confirm room selection.

This stage shows a summary of the selection and waits for confirmation
before proceeding to guest details.
"""

from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from .base import BookingStage, StageAction, StageResult


class BookHotelConfirmSelectionTool(BookingStage):
    """
    Confirm the room selection.

    Shows a summary and waits for user confirmation.
    """

    def __init__(self):
        super().__init__(name="confirm_selection", stage_index=4)

    @property
    def description(self) -> str:
        return "Show selection summary and wait for confirmation"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Confirm selection and proceed.

        Args:
            browser_controller: BrowserController instance
            context: Must contain selected_hotel and selected_room

        Returns:
            StageResult with WAIT_FOR_CONFIRMATION action
        """
        selected_hotel = context.get("selected_hotel", {})
        selected_room = context.get("selected_room", {})

        if not selected_hotel or not selected_room:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error="Missing hotel or room selection",
            )

        # Build summary
        summary = {
            "hotel": selected_hotel.get("name"),
            "room": selected_room.get("name"),
            "checkin": context.get("checkin"),
            "checkout": context.get("checkout"),
            "guests": context.get("guests"),
            "rooms": context.get("rooms"),
            "price": selected_room.get("price") or selected_hotel.get("price"),
        }

        logger.info(f"[BookHotelConfirmSelection] Summary: {summary}")

        return StageResult(
            stage=self.name,
            data={"summary": summary},
            action=StageAction.WAIT_FOR_CONFIRMATION,
            message=self._build_confirmation_message(summary),
            options=[{"confirm": True, "text": "Confirm and continue"}],
        )

    def _build_confirmation_message(self, summary: dict) -> str:
        """Build a confirmation message."""
        parts = [
            f"您已选择: {summary['hotel']}",
            f"房型: {summary['room']}",
            f"入住: {summary['checkin']} - 退房: {summary['checkout']}",
            f"人数: {summary['guests']}人",
        ]

        if summary.get("price"):
            parts.append(f"价格: {summary['price']}")

        parts.append("确认预订吗?")
        return "\n".join(parts)
