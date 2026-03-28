"""
Stage 7: Finalize booking (payment page).

This stage completes the booking flow by clicking "Book" button
and confirming the user reaches the payment page.
"""

from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from ..exceptions import BrowserError
from .base import BookingStage, StageAction, StageResult


class BookHotelFinalizeTool(BookingStage):
    """
    Finalize the booking.

    Clicks the final booking button and confirms user reaches payment page.
    Note: Does NOT complete payment - user must do that manually.
    """

    def __init__(self):
        super().__init__(name="finalize", stage_index=6)

    @property
    def description(self) -> str:
        return "Complete booking flow and reach payment page"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Finalize booking and reach payment page.

        Args:
            browser_controller: BrowserController instance
            context: Booking context

        Returns:
            StageResult with COMPLETE action
        """
        logger.info("[BookHotelFinalize] Completing booking...")

        try:
            # Find and click the "Book" button
            clicked = await self._click_book_button(browser_controller)

            if not clicked:
                return StageResult(
                    stage=self.name,
                    action=StageAction.ERROR,
                    error="Could not find or click Book button",
                )

            # Wait for navigation to payment page
            import asyncio
            await asyncio.sleep(3)

            # Verify we're on payment page or booking confirmed
            current_url = await browser_controller.evaluate_script(
                "() => window.location.href"
            )
            page_text = await browser_controller.evaluate_script(
                "() => document.body.innerText.substring(0, 1000)"
            )

            # Check if we're on payment page
            is_payment_page = any(
                keyword in current_url.lower() or keyword in page_text.lower()
                for keyword in ["payment", "pay", "checkout", "confirm", "booked"]
            )

            logger.info(f"[BookHotelFinalize] Current URL: {current_url}")

            return StageResult(
                stage=self.name,
                data={
                    "final_url": current_url,
                    "is_payment_page": is_payment_page,
                },
                action=StageAction.COMPLETE,
                message=self._build_completion_message(current_url, is_payment_page),
            )

        except BrowserError as e:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Booking failed: {e}",
            )

    async def _click_book_button(self, bc: BrowserController) -> bool:
        """Find and click the primary booking button."""
        try:
            result = await bc.evaluate_script(
                """
                () => {
                    // Look for primary book button
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const primaryBookButtons = buttons.filter(btn => {
                        const text = (btn.innerText || '').toLowerCase();
                        const classes = (btn.className || '').toLowerCase();
                        return (text.includes('book') && text.includes('confirm')) ||
                               classes.includes('book') && classes.includes('primary') ||
                               classes.includes('submit');
                    });

                    if (primaryBookButtons.length > 0) {
                        primaryBookButtons[0].click();
                        return true;
                    }

                    // Fallback: any button with "Book" text
                    for (const btn of buttons) {
                        const text = (btn.innerText || '').toLowerCase();
                        if (text.includes('book') && text.length < 30) {
                            btn.click();
                            return true;
                        }
                    }

                    return false;
                }
                """
            )
            return bool(result)

        except Exception as e:
            logger.error(f"[BookHotelFinalize] Book button click failed: {e}")
            return False

    def _build_completion_message(self, url: str, is_payment_page: bool) -> str:
        """Build completion message."""
        if is_payment_page:
            return (
                "预订已完成！\n"
                "现在您已到达支付页面。\n"
                "请手动完成支付流程。\n"
                f"预订链接: {url}\n"
                "重要提醒：请在支付页面完成后自行确认预订。"
            )
        else:
            return (
                "预订流程已启动。\n"
                "请在浏览器中完成剩余步骤。\n"
                f"当前页面: {url}"
            )
