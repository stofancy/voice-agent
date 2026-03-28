"""
Integration tests for full booking flow.

Requires Chrome running with remote debugging:
Chrome --remote-debugging-port=9222

Run with:
.venv/bin/python -m pytest tests/integration/browser/ -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.server.browser.stages.base import TurnContext, StageAction
from src.server.browser.stages import (
    BookHotelSearchTool,
    BookHotelSelectHotelTool,
    BookHotelNavigatePropertyTool,
    BookHotelSelectRoomTool,
    BookHotelConfirmSelectionTool,
    BookHotelFillGuestTool,
    BookHotelFinalizeTool,
)


class MockBrowserController:
    """Mock BrowserController for testing without real Chrome."""

    def __init__(self):
        self.current_url = "https://www.booking.com"
        self.page_id = 1
        self.screenshot_dir = "/tmp/test_screenshots"

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def navigate(self, url):
        self.current_url = url

    async def evaluate_script(self, script):
        return None

    async def take_snapshot(self, file_path=None):
        class Result:
            text = "mock snapshot"
            file_path = "/tmp/mock_snapshot.txt"
            page_id = 1
        return Result()

    async def extract_hotel_data(self):
        return [
            {
                "name": "Test Hotel A",
                "price": "CNY 1,000",
                "score": "9.0",
                "location": "Tokyo",
                "url": "https://www.booking.com/hotel/test-a",
            },
            {
                "name": "Test Hotel B",
                "price": "CNY 2,000",
                "score": "9.5",
                "location": "Tokyo",
                "url": "https://www.booking.com/hotel/test-b",
            },
        ]

    async def check_login_status(self):
        return {"hasSignIn": False, "hasRegister": False, "hasBookingSession": False}


class TestBookingFlowIntegration:
    """Integration tests for the booking flow."""

    @pytest.fixture
    def mock_bc(self):
        """Create mock browser controller."""
        return MockBrowserController()

    @pytest.fixture
    def turn_context(self):
        """Create turn context for testing."""
        return TurnContext(session_id="test-session-123")

    @pytest.mark.asyncio
    async def test_search_stage(self, mock_bc, turn_context):
        """Test Stage 1: Search."""
        tool = BookHotelSearchTool()

        # Update context with search parameters
        turn_context.update(
            location="Tokyo",
            checkin="2026-04-01",
            checkout="2026-04-05",
            guests=2,
            rooms=1,
        )

        # Execute search stage
        result = await tool.execute(mock_bc, turn_context.booking_data)

        assert result.action == StageAction.CONTINUE
        assert "Tokyo" in result.data.get("location", "")
        assert result.data.get("checkin") == "2026-04-01"
        assert result.data.get("checkout") == "2026-04-05"

    @pytest.mark.asyncio
    async def test_select_hotel_stage(self, mock_bc, turn_context):
        """Test Stage 2: Select Hotel."""
        tool = BookHotelSelectHotelTool()

        result = await tool.execute(mock_bc, turn_context.booking_data)

        assert result.action == StageAction.WAIT_FOR_SELECTION
        assert result.data.get("count") == 2
        assert len(result.options) == 2
        assert result.options[0]["name"] == "Test Hotel A"
        assert result.options[1]["name"] == "Test Hotel B"

    @pytest.mark.asyncio
    async def test_navigate_property_stage(self, mock_bc, turn_context):
        """Test Stage 3: Navigate to property."""
        tool = BookHotelNavigatePropertyTool()

        # Set selected hotel
        turn_context.update(
            selected_hotel={
                "name": "Test Hotel A",
                "url": "https://www.booking.com/hotel/test-a",
            }
        )

        result = await tool.execute(mock_bc, turn_context.booking_data)

        assert result.action == StageAction.CONTINUE
        assert result.data.get("hotel_name") == "Test Hotel A"

    @pytest.mark.asyncio
    async def test_confirm_selection_stage(self, turn_context):
        """Test Stage 5: Confirm Selection."""
        tool = BookHotelConfirmSelectionTool()

        # Set up context with selections
        turn_context.update(
            selected_hotel={"name": "Test Hotel A", "price": "CNY 1,000"},
            selected_room={"name": "Double Room", "price": "CNY 800"},
            checkin="2026-04-01",
            checkout="2026-04-05",
            guests=2,
        )

        result = await tool.execute(None, turn_context.booking_data)

        assert result.action == StageAction.WAIT_FOR_CONFIRMATION
        assert "Test Hotel A" in result.message
        assert "Double Room" in result.message

    @pytest.mark.asyncio
    async def test_fill_guest_stage(self, mock_bc, turn_context):
        """Test Stage 6: Fill Guest Info."""
        tool = BookHotelFillGuestTool()

        turn_context.update(
            guest_name="John Doe",
            guest_email="john@example.com",
        )

        # Mock evaluate_script to return success for form filling
        mock_bc.evaluate_script = AsyncMock(return_value=None)
        result = await tool.execute(mock_bc, turn_context.booking_data)

        assert result.action == StageAction.CONTINUE
        assert result.data.get("guest_name") == "John Doe"
        assert result.data.get("guest_email") == "john@example.com"

    @pytest.mark.asyncio
    async def test_finalize_stage(self, mock_bc):
        """Test Stage 7: Finalize."""
        tool = BookHotelFinalizeTool()

        # Mock evaluate_script to return payment page URL and text
        async def mock_evaluate(script):
            if "window.location.href" in script:
                return "https://www.booking.com/payment.html"
            elif "innerText" in script:
                return "Payment - Complete your booking"
            return None

        mock_bc.evaluate_script = mock_evaluate
        result = await tool.execute(mock_bc, {})

        assert result.action == StageAction.COMPLETE
        assert result.data.get("is_payment_page") is True


class TestTurnContextIntegration:
    """Integration tests for TurnContext with booking flow."""

    def test_full_booking_context(self):
        """Test context through full booking flow."""
        ctx = TurnContext("test-booking")

        # Stage 1: Search
        ctx.update(
            location="Tokyo",
            checkin="2026-04-01",
            checkout="2026-04-05",
            guests=2,
            rooms=1,
        )
        assert ctx.get("location") == "Tokyo"

        # Stage 2: Hotel selected
        ctx.set_selected(
            "hotel",
            {
                "name": "Test Hotel",
                "price": "CNY 1000",
                "url": "https://...",
            },
        )
        assert ctx.get_selected("hotel")["name"] == "Test Hotel"

        # Stage 4: Room selected
        ctx.set_selected(
            "room",
            {
                "name": "Double Room",
                "price": "CNY 800",
            },
        )

        # Stage 6: Guest info
        ctx.update(guest_name="John Doe", guest_email="john@example.com")

        # Verify all data
        assert ctx.get("location") == "Tokyo"
        assert ctx.get_selected("hotel")["name"] == "Test Hotel"
        assert ctx.get_selected("room")["name"] == "Double Room"
        assert ctx.get("guest_name") == "John Doe"

    def test_pause_and_resume(self):
        """Test pause/resume during booking."""
        ctx = TurnContext("test-booking")

        # Simulate mid-booking state
        ctx.update(location="Tokyo", checkin="2026-04-01")
        ctx.advance_stage()  # Move to stage 1
        ctx.set_selected("hotel", {"name": "Test Hotel"})

        # Pause
        state = ctx.pause()

        # Simulate new context (e.g., after interruption)
        ctx2 = TurnContext("new-session")
        ctx2.resume(state)

        # Verify state restored
        assert ctx2.session_id == "test-booking"
        assert ctx2.current_stage_index == 1
        assert ctx2.get("location") == "Tokyo"
        assert ctx2.get_selected("hotel")["name"] == "Test Hotel"


class TestStageResultSerialization:
    """Test StageResult serialization for API responses."""

    def test_stage_result_to_dict(self):
        """Test StageResult serializes correctly."""
        from src.server.browser.stages.base import StageResult, StageAction

        result = StageResult(
            stage="select_hotel",
            action=StageAction.WAIT_FOR_SELECTION,
            data={"hotels": [], "count": 0},
            message="Select a hotel",
            options=[{"index": 1, "name": "Hotel A"}],
        )

        d = result.to_dict()

        assert d["stage"] == "select_hotel"
        assert d["action"] == "wait_for_selection"
        assert d["message"] == "Select a hotel"
        assert len(d["options"]) == 1
        assert d["options"][0]["index"] == 1

    def test_error_result(self):
        """Test error StageResult."""
        from src.server.browser.stages.base import StageResult, StageAction

        result = StageResult(
            stage="search",
            action=StageAction.ERROR,
            error="Navigation failed",
        )

        d = result.to_dict()

        assert d["action"] == "error"
        assert d["error"] == "Navigation failed"
