"""
Stage 6: Fill guest information.

This stage fills in the guest details form on Booking.com.
"""

import asyncio
from typing import Any

from loguru import logger

from ..browser_controller import BrowserController
from ..exceptions import BrowserError
from .base import BookingStage, StageAction, StageResult


class BookHotelFillGuestTool(BookingStage):
    """
    Fill in guest information.

    Enters guest name and email into the booking form.
    """

    def __init__(self):
        super().__init__(name="fill_guest", stage_index=5)

    @property
    def description(self) -> str:
        return "Fill guest name and contact information"

    async def execute(
        self,
        browser_controller: BrowserController,
        context: dict[str, Any],
    ) -> StageResult:
        """
        Fill guest information form.

        Args:
            browser_controller: BrowserController instance
            context: Must contain guest_name and guest_email

        Returns:
            StageResult with CONTINUE action
        """
        guest_name = context.get("guest_name")
        guest_email = context.get("guest_email")

        if not guest_name:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error="Missing required field: guest_name",
            )

        logger.info(f"[BookHotelFillGuest] Filling form for: {guest_name}")

        try:
            # Scroll to guest form area
            await browser_controller.evaluate_script(
                """
                () => {
                    const forms = document.querySelectorAll('form');
                    for (const form of forms) {
                        if (form.innerText.toLowerCase().includes('guest') ||
                            form.innerText.toLowerCase().includes('name') ||
                            form.innerText.toLowerCase().includes('contact')) {
                            form.scrollIntoView({ behavior: 'smooth' });
                            return;
                        }
                    }
                }
                """
            )
            await asyncio.sleep(1)

            # Fill in guest name
            await self._fill_field(browser_controller, "name", guest_name)

            # Fill in email if provided
            if guest_email:
                await self._fill_field(browser_controller, "email", guest_email)
                await asyncio.sleep(0.3)

            # Check for any special requests field and leave it blank
            await browser_controller.evaluate_script(
                """
                () => {
                    const textareas = document.querySelectorAll('textarea');
                    for (const ta of textareas) {
                        const label = ta.closest('label')?.innerText || '';
                        if (label.toLowerCase().includes('special') ||
                            label.toLowerCase().includes('request')) {
                            // Leave blank - not required
                            return;
                        }
                    }
                }
                """
            )

            return StageResult(
                stage=self.name,
                data={"guest_name": guest_name, "guest_email": guest_email},
                action=StageAction.CONTINUE,
                message="Guest information entered. Proceeding to payment.",
            )

        except BrowserError as e:
            return StageResult(
                stage=self.name,
                action=StageAction.ERROR,
                error=f"Failed to fill guest form: {e}",
            )

    async def _fill_field(self, bc: BrowserController, field_type: str, value: str) -> None:
        """Fill a specific form field by type."""
        try:
            await bc.evaluate_script(
                f"""
                () => {{
                    // Find input by name, type, or aria-label
                    const inputs = Array.from(document.querySelectorAll('input, textarea'));
                    for (const input of inputs) {{
                        const name = input.name || '';
                        const type = input.type || '';
                        const ariaLabel = (input.getAttribute('aria-label') || '').toLowerCase();
                        const placeholder = (input.placeholder || '').toLowerCase();

                        let match = false;
                        if ('{field_type}' === 'name') {{
                            match = name.includes('name') || ariaLabel.includes('name') ||
                                   placeholder.includes('name') || ariaLabel.includes('guest');
                        }} else if ('{field_type}' === 'email') {{
                            match = name.includes('email') || type === 'email' ||
                                   ariaLabel.includes('email') || placeholder.includes('email');
                        }} else if ('{field_type}' === 'phone') {{
                            match = name.includes('phone') || type === 'tel' ||
                                   ariaLabel.includes('phone') || placeholder.includes('phone');
                        }}

                        if (match) {{
                            input.value = '{value.replace("'", "\\'")}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return;
                        }}
                    }}
                }}
                """
            )
        except Exception as e:
            logger.warning(f"[BookHotelFillGuest] Could not fill {field_type} field: {e}")
