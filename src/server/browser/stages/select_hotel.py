"""
Stage 2: Select hotel from search results.

This stage extracts hotel data from the search results page
and presents options to the user for selection.
"""

from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from .base import BookingStage, StageAction, StageResult


class BookHotelSelectHotelTool(BookingStage):
    """
    Select a hotel from search results.

    Extracts hotel data and waits for user selection.
    """

    def __init__(self):
        super().__init__(name="select_hotel", stage_index=1)

    @property
    def description(self) -> str:
        return "Extract search results and wait for hotel selection"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Extract hotels from results and wait for selection.

        Args:
            browser_controller: BrowserController instance
            context: Booking context with search results

        Returns:
            StageResult with WAIT_FOR_SELECTION action and hotel options
        """
        logger.info("[BookHotelSelectHotel] Extracting hotel data...")

        try:
            # Extract hotel data from the page
            hotels = await browser_controller.extract_hotel_data()

            if not hotels:
                # Fallback: try to get at least some data
                logger.warning("[BookHotelSelectHotel] No hotels extracted, trying direct snapshot")
                hotels = await self._extract_hotels_direct(browser_controller)

            logger.info(f"[BookHotelSelectHotel] Found {len(hotels)} hotels")

            if not hotels:
                return StageResult(
                    stage=self.name,
                    action=StageAction.ERROR,
                    error="No hotels found on the page",
                )

            # Build options for user selection
            options = []
            for i, hotel in enumerate(hotels, 1):
                option = {
                    "index": i,
                    "id": hotel.get("url", f"h{i}"),
                    "name": hotel.get("name", f"Hotel {i}"),
                    "display": self._build_display_string(hotel),
                    "details": hotel,
                }
                options.append(option)

            return StageResult(
                stage=self.name,
                data={"hotels": hotels, "count": len(hotels)},
                action=StageAction.WAIT_FOR_SELECTION,
                message=f"Found {len(hotels)} hotels. Which one would you like?",
                options=options,
            )

        except Exception as e:
            logger.error(f"[BookHotelSelectHotel] Error: {e}")
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Failed to extract hotels: {e}",
            )

    def _build_display_string(self, hotel: dict) -> str:
        """Build a display string for a hotel option."""
        parts = [hotel.get("name", "Unknown Hotel")]

        if hotel.get("price"):
            parts.append(hotel["price"])

        if hotel.get("score"):
            parts.append(f"评分: {hotel['score']}")

        if hotel.get("location"):
            parts.append(hotel["location"])

        return " - ".join(parts)

    async def _extract_hotels_direct(self, bc: BrowserController) -> list[dict]:
        """Extract hotels using direct JavaScript evaluation."""
        try:
            result = await bc.evaluate_script(
                """
                () => {
                    const cards = document.querySelectorAll('[data-testid="property-card"]');
                    const results = [];

                    for (let i = 0; i < Math.min(cards.length, 20); i++) {
                        const card = cards[i];
                        const nameEl = card.querySelector('[data-testid="title"]');
                        const priceEl = card.querySelector('[data-testid*="price"]');
                        const scoreEl = card.querySelector('[data-testid="review-score"]');
                        const locationEl = card.querySelector('[data-testid="location"]');

                        results.push({
                            name: nameEl?.innerText || 'Unknown',
                            price: priceEl?.innerText || null,
                            score: scoreEl?.innerText?.match(/\\d+\\.?\\d*/)?.[0] || null,
                            location: locationEl?.innerText || null,
                            url: card.querySelector('a')?.href || null
                        });
                    }

                    return results;
                }
                """
            )
            return result or []
        except Exception as e:
            logger.error(f"[BookHotelSelectHotel] Direct extraction failed: {e}")
            return []
