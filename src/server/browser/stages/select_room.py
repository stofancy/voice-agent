"""
Stage 4: Select room type on property page.

This stage extracts available room types and presents options
for the user to select.
"""

from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from .base import BookingStage, StageAction, StageResult


class BookHotelSelectRoomTool(BookingStage):
    """
    Select a room type from available options.

    Extracts room data from property page and waits for selection.
    """

    def __init__(self):
        super().__init__(name="select_room", stage_index=3)

    @property
    def description(self) -> str:
        return "Extract room types and wait for room selection"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Extract rooms and wait for selection.

        Args:
            browser_controller: BrowserController instance
            context: Booking context

        Returns:
            StageResult with WAIT_FOR_SELECTION action and room options
        """
        logger.info("[BookHotelSelectRoom] Extracting room data...")

        try:
            # Extract room data from property page
            rooms = await self._extract_rooms(browser_controller)

            if not rooms:
                return StageResult(
                    stage=self.name,
                    action=StageAction.ERROR,
                    error="No rooms found on the page",
                )

            logger.info(f"[BookHotelSelectRoom] Found {len(rooms)} room options")

            # Build options
            options = []
            for i, room in enumerate(rooms, 1):
                option = {
                    "index": i,
                    "id": room.get("id", f"r{i}"),
                    "name": room.get("name", f"Room {i}"),
                    "display": self._build_display_string(room),
                    "details": room,
                }
                options.append(option)

            return StageResult(
                stage=self.name,
                data={"rooms": rooms, "count": len(rooms)},
                action=StageAction.WAIT_FOR_SELECTION,
                message=f"Found {len(rooms)} room options. Which room would you like?",
                options=options,
            )

        except Exception as e:
            logger.error(f"[BookHotelSelectRoom] Error: {e}")
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Failed to extract rooms: {e}",
            )

    def _build_display_string(self, room: dict) -> str:
        """Build display string for a room option."""
        parts = [room.get("name", "Unknown Room")]

        if room.get("price"):
            parts.append(room["price"])

        if room.get("max_guests"):
            parts.append(f"最多 {room['max_guests']} 人")

        if room.get("bed_type"):
            parts.append(room["bed_type"])

        return " - ".join(parts)

    async def _extract_rooms(self, bc: BrowserController) -> list[dict]:
        """Extract room data from property page."""
        try:
            result = await bc.evaluate_script(
                """
                () => {
                    // Look for room cards/containers
                    const roomContainers = document.querySelectorAll(
                        '[data-testid="room-card"], .room-card, .room-container, [data-testid="property-room-card"]'
                    );

                    const rooms = [];

                    if (roomContainers.length === 0) {
                        // Try alternative selectors
                        const h2Elements = Array.from(document.querySelectorAll('h2, h3'));
                        for (const h2 of h2Elements) {
                            const text = h2.innerText || '';
                            if (text.includes('Standard') || text.includes('Double') ||
                                text.includes('Twin') || text.includes('Suite') ||
                                text.includes('Room')) {
                                const parent = h2.closest('.room-card, .room-container, [data-testid]');
                                if (parent) {
                                    const priceEl = parent.querySelector('[data-testid="price-and-discounted-price"]');
                                    rooms.push({
                                        name: text.substring(0, 50),
                                        price: priceEl?.innerText || null,
                                        id: parent.getAttribute('data-testid') || null
                                    });
                                }
                            }
                        }
                    } else {
                        for (let i = 0; i < Math.min(roomContainers.length, 10); i++) {
                            const room = roomContainers[i];
                            const nameEl = room.querySelector('[data-testid="room-name"]');
                            const priceEl = room.querySelector('[data-testid*="price"]');
                            const bedsEl = room.querySelector('.bed-type, [data-testid="bed-type"]');

                            rooms.push({
                                name: nameEl?.innerText || `Room ${i + 1}`,
                                price: priceEl?.innerText || null,
                                max_guests: null,
                                bed_type: bedsEl?.innerText || null,
                                id: room.getAttribute('data-testid') || `room-${i}`
                            });
                        }
                    }

                    return rooms;
                }
                """
            )
            return result or []

        except Exception as e:
            logger.error(f"[BookHotelSelectRoom] Extraction failed: {e}")
            return []
