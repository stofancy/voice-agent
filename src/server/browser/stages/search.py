"""
Stage 1: Search hotels on Booking.com.

This stage navigates to Booking.com and performs a hotel search
based on user-provided location, dates, and guest count.
"""

import asyncio
from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from ..exceptions import BrowserError, NavigationError
from .base import BookingStage, StageAction, StageResult


class BookHotelSearchTool(BookingStage):
    """
    Search for hotels on Booking.com.

    User provides: location, check-in date, check-out date, guests/rooms
    """

    def __init__(self):
        super().__init__(name="search", stage_index=0)

    @property
    def description(self) -> str:
        return "Search for hotels on Booking.com with location, dates, and guest count"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Execute hotel search.

        Args:
            browser_controller: BrowserController instance
            context: Must contain location, checkin, checkout, guests

        Returns:
            StageResult with CONTINUE action (search results handled by select_hotel)
        """
        location = context.get("location")
        checkin = context.get("checkin")
        checkout = context.get("checkout")
        guests = context.get("guests", 1)
        rooms = context.get("rooms", 1)

        if not location:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error="Missing required field: location",
            )

        logger.info(
            f"[BookHotelSearch] Searching: location={location}, "
            f"checkin={checkin}, checkout={checkout}, guests={guests}, rooms={rooms}"
        )

        try:
            # Navigate to Booking.com
            await browser_controller.navigate("https://www.booking.com")

            # Handle consent popup if present
            await self._handle_consent_popup(browser_controller)

            # Fill in search form
            await self._fill_search_form(
                browser_controller,
                location=location,
                checkin=checkin,
                checkout=checkout,
                guests=guests,
                rooms=rooms,
            )

            # Submit search
            await self._submit_search(browser_controller)

            # Wait for results to load
            await asyncio.sleep(2)

            # Verify we're on results page
            current_url = await browser_controller.evaluate_script(
                "() => window.location.href"
            )
            logger.info(f"[BookHotelSearch] Current URL: {current_url}")

            return StageResult(
                stage=self.name,
                data={
                    "location": location,
                    "checkin": checkin,
                    "checkout": checkout,
                    "guests": guests,
                    "rooms": rooms,
                    "search_url": current_url,
                },
                action=StageAction.CONTINUE,
                message=f"Found hotels for {location}. Select one to continue.",
            )

        except NavigationError as e:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Navigation failed: {e}",
            )
        except BrowserError as e:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Browser error: {e}",
            )

    async def _handle_consent_popup(self, bc: BrowserController) -> None:
        """Handle cookie consent popup if present."""
        try:
            # Check for consent popup
            has_popup = await bc.evaluate_script(
                """
                () => {
                    // Look for consent button patterns
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = btn.innerText || '';
                        if (text.toLowerCase().includes('accept') ||
                            text.toLowerCase().includes('agree') ||
                            text.toLowerCase().includes('consent')) {
                            return true;
                        }
                    }
                    // Check for checkbox "Select all"
                    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                    for (const cb of checkboxes) {
                        const label = cb.closest('label')?.innerText || '';
                        if (label.toLowerCase().includes('select all')) {
                            return true;
                        }
                    }
                    return false;
                }
                """
            )

            if has_popup:
                logger.info("[BookHotelSearch] Handling consent popup")

                # Try to click "Select all" checkbox then "Accept"
                await bc.evaluate_script(
                    """
                    () => {
                        // Click "Select all" if present
                        const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
                        for (const cb of checkboxes) {
                            const label = cb.closest('label')?.innerText || '';
                            if (label.toLowerCase().includes('select all')) {
                                cb.click();
                                break;
                            }
                        }
                        // Click accept button
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const btn of buttons) {
                            const text = btn.innerText || '';
                            if (text.toLowerCase().includes('accept') ||
                                text.toLowerCase().includes('agree')) {
                                btn.click();
                                break;
                            }
                        }
                    }
                    """
                )
                await asyncio.sleep(1)

        except Exception as e:
            logger.warning(f"[BookHotelSearch] Could not handle consent popup: {e}")

    async def _fill_search_form(
        self,
        bc: BrowserController,
        location: str,
        checkin: str | None,
        checkout: str | None,
        guests: int,
        rooms: int,
    ) -> None:
        """Fill in the search form fields."""
        try:
            # Find and fill destination field (combobox)
            await bc.evaluate_script(
                f"""
                () => {{
                    // Find the destination combobox
                    const inputs = document.querySelectorAll('input');
                    for (const input of inputs) {{
                        const parent = input.closest('[data-testid]) || input.closest('. destination');
                        if (parent && input.value === '') {{
                            // This might be the destination field
                            const ariaLabel = input.getAttribute('aria-label') || '';
                            if (ariaLabel.toLowerCase().includes('destination') ||
                                ariaLabel.toLowerCase().includes('where')) {{
                                input.value = '{location}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                break;
                            }}
                        }}
                    }}
                }}
                """
            )

            # Alternative: directly set value on any visible text input in search form
            await asyncio.sleep(0.5)

            # Set check-in and check-out dates via URL parameters (more reliable)
            if checkin and checkout:
                logger.info(f"[BookHotelSearch] Setting dates: {checkin} to {checkout}")

                # Click check-in date button first
                await bc.evaluate_script(
                    """
                    () => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const btn of buttons) {
                            const text = btn.innerText || '';
                            if (text.includes('Check-in') || text.includes('Check out')) {
                                btn.click();
                                return;
                            }
                        }
                    }
                    """
                )
                await asyncio.sleep(1)

        except Exception as e:
            logger.warning(f"[BookHotelSearch] Error filling search form: {e}")
            raise

    async def _submit_search(self, bc: BrowserController) -> None:
        """Submit the search form."""
        try:
            await bc.evaluate_script(
                """
                () => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        const text = btn.innerText || '';
                        if (text.includes('Search') && !text.includes('Searching')) {
                            btn.click();
                            return;
                        }
                    }
                }
                """
            )
        except Exception as e:
            logger.error(f"[BookHotelSearch] Failed to submit search: {e}")
            raise

    def should_skip(self, context: dict[str, Any]) -> bool:
        """Skip search if URL already contains search results."""
        return bool(context.get("search_url") and "searchresults" in context.get("search_url", ""))
