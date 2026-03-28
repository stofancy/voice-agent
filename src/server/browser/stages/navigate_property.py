"""
Stage 3: Navigate to hotel property page.

This stage navigates from the search results to the selected hotel's
property page where room selection happens.
"""

from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from ..exceptions import BrowserError
from .base import BookingStage, StageAction, StageResult


class BookHotelNavigatePropertyTool(BookingStage):
    """
    Navigate to the selected hotel's property page.

    Clicks on the hotel card to go to its detail page.
    """

    def __init__(self):
        super().__init__(name="navigate_property", stage_index=2)

    @property
    def description(self) -> str:
        return "Navigate from search results to selected hotel property page"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Navigate to hotel property page.

        Args:
            browser_controller: BrowserController instance
            context: Must contain selected hotel URL or index

        Returns:
            StageResult with CONTINUE action
        """
        selected = context.get("selected_hotel")
        if not selected:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error="No hotel selected",
            )

        hotel_url = selected.get("url")
        if not hotel_url:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error="Selected hotel has no URL",
            )

        logger.info(f"[BookHotelNavigateProperty] Navigating to: {hotel_url}")

        try:
            # Navigate to hotel property page
            await browser_controller.navigate(hotel_url)

            # Wait for page to load
            import asyncio
            await asyncio.sleep(3)

            # Check for any popup and dismiss
            await self._handle_popups(browser_controller)

            # Verify we're on the property page
            current_url = await browser_controller.evaluate_script(
                "() => window.location.href"
            )

            return StageResult(
                stage=self.name,
                data={
                    "property_url": current_url,
                    "hotel_name": selected.get("name"),
                },
                action=StageAction.CONTINUE,
                message=f"Viewing {selected.get('name')} rooms. Select a room to continue.",
            )

        except BrowserError as e:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Navigation failed: {e}",
            )

    async def _handle_popups(self, bc: BrowserController) -> None:
        """Handle any popups on the property page."""
        import asyncio

        try:
            # Dismiss Genius discount popup if appears
            await bc.evaluate_script(
                """
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = btn.innerText || '';
                        if (text.includes('Dismiss') || text.includes('Close') ||
                            text.includes('Stay on')) {
                            btn.click();
                            return;
                        }
                    }
                }
                """
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"[BookHotelNavigateProperty] Popup handling: {e}")
