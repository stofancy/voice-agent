"""
Unit tests for booking stage tools.
"""

import pytest
from unittest.mock import AsyncMock
from src.server.browser.stages.base import (
    BookingStage,
    StageResult,
    StageAction,
    TurnContext,
)


class TestStageAction:
    """Tests for StageAction enum."""

    def test_stage_action_values(self):
        """Test all StageAction values exist."""
        assert StageAction.CONTINUE.value == "continue"
        assert StageAction.WAIT_FOR_SELECTION.value == "wait_for_selection"
        assert StageAction.WAIT_FOR_CONFIRMATION.value == "wait_for_confirmation"
        assert StageAction.COMPLETE.value == "complete"
        assert StageAction.ERROR.value == "error"


class TestStageResult:
    """Tests for StageResult dataclass."""

    def test_stage_result_defaults(self):
        """Test StageResult with defaults."""
        result = StageResult(stage="search")
        assert result.stage == "search"
        assert result.action == StageAction.CONTINUE
        assert result.data == {}
        assert result.message == ""
        assert result.options == []
        assert result.error is None

    def test_stage_result_full(self):
        """Test StageResult with all fields."""
        result = StageResult(
            stage="select_hotel",
            action=StageAction.WAIT_FOR_SELECTION,
            data={"hotels": [{"name": "Test Hotel"}]},
            message="Select a hotel",
            options=[{"index": 1, "name": "Test Hotel"}],
        )
        assert result.stage == "select_hotel"
        assert result.action == StageAction.WAIT_FOR_SELECTION
        assert len(result.data["hotels"]) == 1
        assert len(result.options) == 1

    def test_stage_result_to_dict(self):
        """Test StageResult serialization."""
        result = StageResult(
            stage="search",
            action=StageAction.CONTINUE,
            message="Search complete",
        )
        d = result.to_dict()
        assert d["stage"] == "search"
        assert d["action"] == "continue"
        assert d["message"] == "Search complete"


class TestTurnContext:
    """Tests for TurnContext class."""

    def test_turn_context_init(self):
        """Test TurnContext initialization."""
        ctx = TurnContext(session_id="test-session-123")
        assert ctx.session_id == "test-session-123"
        assert ctx.current_stage_index == 0
        assert ctx.booking_data == {}
        assert ctx.user_inputs == []
        assert ctx.errors == []
        assert ctx.selected_items == {}

    def test_update_and_get(self):
        """Test updating and getting values."""
        ctx = TurnContext("test")
        ctx.update(location="Tokyo", checkin="2026-04-01")
        assert ctx.get("location") == "Tokyo"
        assert ctx.get("checkin") == "2026-04-01"
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "default") == "default"

    def test_selected_items(self):
        """Test selected items management."""
        ctx = TurnContext("test")
        hotel = {"name": "Test Hotel", "price": "CNY 1000"}
        ctx.set_selected("hotel", hotel)
        assert ctx.get_selected("hotel") == hotel
        assert ctx.get_selected("room") is None

    def test_advance_stage(self):
        """Test stage advancement."""
        ctx = TurnContext("test")
        assert ctx.current_stage_index == 0
        ctx.advance_stage()
        assert ctx.current_stage_index == 1
        ctx.advance_stage()
        assert ctx.current_stage_index == 2

    def test_add_error(self):
        """Test error recording."""
        ctx = TurnContext("test")
        ctx.add_error("Navigation failed")
        assert len(ctx.errors) == 1
        assert "Navigation failed" in ctx.errors[0]

    def test_add_user_input(self):
        """Test user input recording."""
        ctx = TurnContext("test")
        ctx.add_user_input("Find hotels in Tokyo")
        ctx.add_user_input("Select the second one")
        assert len(ctx.user_inputs) == 2

    def test_pause_and_resume(self):
        """Test session pause and resume."""
        ctx = TurnContext("test-session")
        ctx.update(location="Tokyo", checkin="2026-04-01")
        ctx.advance_stage()
        ctx.advance_stage()
        ctx.set_selected("hotel", {"name": "Test Hotel"})
        ctx.add_user_input("Find hotels")

        # Pause
        state = ctx.pause()

        # Create new context and resume
        ctx2 = TurnContext("different-session")
        ctx2.resume(state)

        assert ctx2.session_id == "test-session"
        assert ctx2.current_stage_index == 2
        assert ctx2.get("location") == "Tokyo"
        assert ctx2.get_selected("hotel") == {"name": "Test Hotel"}
        assert len(ctx2.user_inputs) == 1

    def test_get_state_and_restore_state(self):
        """Test get_state and restore_state methods."""
        ctx = TurnContext("test")
        ctx.update(test_key="test_value")

        # get_state should work like pause
        state = ctx.get_state()
        assert state["booking_data"]["test_key"] == "test_value"

        # restore_state should work like resume
        ctx2 = TurnContext("new-session")
        ctx2.restore_state(state)
        assert ctx2.get("test_key") == "test_value"

    def test_is_paused_property(self):
        """Test is_paused property."""
        ctx = TurnContext("test")
        assert ctx.is_paused is False
        ctx.is_paused = True
        assert ctx.is_paused is True


class TestBookingStageAbstract:
    """Tests for BookingStage abstract base class."""

    def test_booking_stage_is_abstract(self):
        """Test that BookingStage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BookingStage("test", 0)

    def test_booking_stage_subclass(self):
        """Test that a proper subclass can be created."""

        class TestStage(BookingStage):
            @property
            def description(self) -> str:
                return "Test stage"

            async def execute(self, browser_controller, context):
                return StageResult(stage="test")

        stage = TestStage("test", 1)
        assert stage.name == "test"
        assert stage.stage_index == 1
        assert stage.description == "Test stage"
        assert stage.should_skip({}) is False  # Default implementation


class TestBookHotelSelectHotelTool:
    """Tests for BookHotelSelectHotelTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.select_hotel import BookHotelSelectHotelTool

        tool = BookHotelSelectHotelTool()
        assert tool.name == "select_hotel"
        assert tool.stage_index == 1

    def test_build_display_string(self):
        """Test display string building."""
        from src.server.browser.stages.select_hotel import BookHotelSelectHotelTool

        tool = BookHotelSelectHotelTool()

        hotel = {
            "name": "Test Hotel",
            "price": "CNY 1,234",
            "score": "9.5",
            "location": "Tokyo",
        }
        display = tool._build_display_string(hotel)
        assert "Test Hotel" in display
        assert "CNY 1,234" in display
        assert "9.5" in display
        assert "Tokyo" in display

    def test_build_display_string_minimal(self):
        """Test display string with minimal data."""
        from src.server.browser.stages.select_hotel import BookHotelSelectHotelTool

        tool = BookHotelSelectHotelTool()
        hotel = {"name": "Minimal Hotel"}
        display = tool._build_display_string(hotel)
        assert display == "Minimal Hotel"

    # Note: Natural language selection parsing (e.g., "第二个", "贵一点的")
    # is handled by the LLM/BookingAgent layer, not by this stage tool.
    # See tests for BookingAgent if you need to test selection logic.


class TestBookHotelSearchTool:
    """Tests for BookHotelSearchTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.search import BookHotelSearchTool

        tool = BookHotelSearchTool()
        assert tool.name == "search"
        assert tool.stage_index == 0


class TestBookHotelNavigatePropertyTool:
    """Tests for BookHotelNavigatePropertyTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.navigate_property import BookHotelNavigatePropertyTool

        tool = BookHotelNavigatePropertyTool()
        assert tool.name == "navigate_property"
        assert tool.stage_index == 2

    @pytest.mark.asyncio
    async def test_execute_navigates_to_hotel(self):
        """Test execute navigates to selected hotel URL."""
        from src.server.browser.stages.navigate_property import BookHotelNavigatePropertyTool
        from unittest.mock import AsyncMock

        tool = BookHotelNavigatePropertyTool()
        mock_bc = AsyncMock()
        mock_bc.navigate = AsyncMock()
        mock_bc.evaluate_script = AsyncMock(return_value="https://www.booking.com/hotel/test")

        context = {
            "selected_hotel": {
                "name": "Test Hotel",
                "url": "https://www.booking.com/hotel/test",
            }
        }

        result = await tool.execute(mock_bc, context)

        assert result.action == StageAction.CONTINUE
        assert result.data.get("hotel_name") == "Test Hotel"
        mock_bc.navigate.assert_called_once_with("https://www.booking.com/hotel/test")

    @pytest.mark.asyncio
    async def test_execute_error_no_hotel_selected(self):
        """Test execute returns error when no hotel selected."""
        from src.server.browser.stages.navigate_property import BookHotelNavigatePropertyTool

        tool = BookHotelNavigatePropertyTool()
        result = await tool.execute(None, {})

        assert result.action == StageAction.ERROR
        assert "No hotel selected" in result.error

    @pytest.mark.asyncio
    async def test_execute_error_no_url(self):
        """Test execute returns error when hotel has no URL."""
        from src.server.browser.stages.navigate_property import BookHotelNavigatePropertyTool

        tool = BookHotelNavigatePropertyTool()
        context = {"selected_hotel": {"name": "Test Hotel"}}

        result = await tool.execute(None, context)

        assert result.action == StageAction.ERROR
        assert "no URL" in result.error


class TestBookHotelSelectRoomTool:
    """Tests for BookHotelSelectRoomTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.select_room import BookHotelSelectRoomTool

        tool = BookHotelSelectRoomTool()
        assert tool.name == "select_room"
        assert tool.stage_index == 3

    def test_build_display_string(self):
        """Test room display string building."""
        from src.server.browser.stages.select_room import BookHotelSelectRoomTool

        tool = BookHotelSelectRoomTool()

        room = {
            "name": "Standard Double Room",
            "price": "CNY 800",
            "max_guests": 2,
            "bed_type": "1 double bed",
        }
        display = tool._build_display_string(room)
        assert "Standard Double Room" in display
        assert "CNY 800" in display
        assert "最多 2 人" in display

    @pytest.mark.asyncio
    async def test_execute_returns_room_options(self):
        """Test execute returns WAIT_FOR_SELECTION with room options."""
        from src.server.browser.stages.select_room import BookHotelSelectRoomTool

        tool = BookHotelSelectRoomTool()
        mock_bc = AsyncMock()
        mock_bc.evaluate_script = AsyncMock(return_value=[
            {"name": "Standard Room", "price": "CNY 500", "id": "r1"},
            {"name": "Deluxe Room", "price": "CNY 800", "id": "r2"},
        ])

        result = await tool.execute(mock_bc, {})

        assert result.action == StageAction.WAIT_FOR_SELECTION
        assert result.data.get("count") == 2
        assert len(result.options) == 2
        assert result.options[0]["name"] == "Standard Room"
        assert result.options[1]["name"] == "Deluxe Room"

    @pytest.mark.asyncio
    async def test_execute_error_no_rooms(self):
        """Test execute returns error when no rooms found."""
        from src.server.browser.stages.select_room import BookHotelSelectRoomTool

        tool = BookHotelSelectRoomTool()
        mock_bc = AsyncMock()
        mock_bc.evaluate_script = AsyncMock(return_value=[])

        result = await tool.execute(mock_bc, {})

        assert result.action == StageAction.ERROR
        assert "No rooms found" in result.error


class TestBookHotelConfirmSelectionTool:
    """Tests for BookHotelConfirmSelectionTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.confirm_selection import BookHotelConfirmSelectionTool

        tool = BookHotelConfirmSelectionTool()
        assert tool.name == "confirm_selection"
        assert tool.stage_index == 4

    def test_build_confirmation_message(self):
        """Test confirmation message building."""
        from src.server.browser.stages.confirm_selection import BookHotelConfirmSelectionTool

        tool = BookHotelConfirmSelectionTool()

        summary = {
            "hotel": "Test Hotel",
            "room": "Double Room",
            "checkin": "2026-04-01",
            "checkout": "2026-04-05",
            "guests": 2,
            "price": "CNY 5,000",
        }

        message = tool._build_confirmation_message(summary)
        assert "Test Hotel" in message
        assert "Double Room" in message
        assert "2026-04-01" in message
        assert "2026-04-05" in message
        assert "2人" in message
        assert "CNY 5,000" in message

    @pytest.mark.asyncio
    async def test_execute_returns_wait_for_confirmation(self):
        """Test execute returns WAIT_FOR_CONFIRMATION with summary."""
        from src.server.browser.stages.confirm_selection import BookHotelConfirmSelectionTool

        tool = BookHotelConfirmSelectionTool()
        context = {
            "selected_hotel": {"name": "Test Hotel", "price": "CNY 1000"},
            "selected_room": {"name": "Double Room", "price": "CNY 800"},
            "checkin": "2026-04-01",
            "checkout": "2026-04-05",
            "guests": 2,
        }

        result = await tool.execute(None, context)

        assert result.action == StageAction.WAIT_FOR_CONFIRMATION
        assert result.data["summary"]["hotel"] == "Test Hotel"
        assert result.data["summary"]["room"] == "Double Room"

    @pytest.mark.asyncio
    async def test_execute_error_missing_hotel(self):
        """Test execute returns error when hotel not selected."""
        from src.server.browser.stages.confirm_selection import BookHotelConfirmSelectionTool

        tool = BookHotelConfirmSelectionTool()
        result = await tool.execute(None, {"selected_room": {"name": "Double Room"}})

        assert result.action == StageAction.ERROR
        assert "Missing hotel or room" in result.error


class TestBookHotelFillGuestTool:
    """Tests for BookHotelFillGuestTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.fill_guest import BookHotelFillGuestTool

        tool = BookHotelFillGuestTool()
        assert tool.name == "fill_guest"
        assert tool.stage_index == 5

    @pytest.mark.asyncio
    async def test_execute_fills_guest_info(self):
        """Test execute fills guest information."""
        from src.server.browser.stages.fill_guest import BookHotelFillGuestTool

        tool = BookHotelFillGuestTool()
        mock_bc = AsyncMock()
        mock_bc.evaluate_script = AsyncMock()

        context = {
            "guest_name": "John Doe",
            "guest_email": "john@example.com",
        }

        result = await tool.execute(mock_bc, context)

        assert result.action == StageAction.CONTINUE
        assert result.data.get("guest_name") == "John Doe"
        assert result.data.get("guest_email") == "john@example.com"

    @pytest.mark.asyncio
    async def test_execute_error_missing_guest_name(self):
        """Test execute returns error when guest_name is missing."""
        from src.server.browser.stages.fill_guest import BookHotelFillGuestTool

        tool = BookHotelFillGuestTool()
        result = await tool.execute(None, {"guest_email": "test@test.com"})

        assert result.action == StageAction.ERROR
        assert "guest_name" in result.error


class TestBookHotelFinalizeTool:
    """Tests for BookHotelFinalizeTool."""

    def test_tool_creation(self):
        """Test tool can be created."""
        from src.server.browser.stages.finalize import BookHotelFinalizeTool

        tool = BookHotelFinalizeTool()
        assert tool.name == "finalize"
        assert tool.stage_index == 6

    def test_build_completion_message_payment_page(self):
        """Test completion message for payment page."""
        from src.server.browser.stages.finalize import BookHotelFinalizeTool

        tool = BookHotelFinalizeTool()

        message = tool._build_completion_message(
            "https://www.booking.com/payment.html",
            is_payment_page=True,
        )
        assert "预订已完成" in message
        assert "支付页面" in message
        assert "手动完成" in message

    def test_build_completion_message_other(self):
        """Test completion message when not payment page."""
        from src.server.browser.stages.finalize import BookHotelFinalizeTool

        tool = BookHotelFinalizeTool()

        message = tool._build_completion_message(
            "https://www.booking.com/other.html",
            is_payment_page=False,
        )
        assert "预订流程已启动" in message

    @pytest.mark.asyncio
    async def test_execute_complete_with_payment_page(self):
        """Test execute completes when payment page reached."""
        from src.server.browser.stages.finalize import BookHotelFinalizeTool

        tool = BookHotelFinalizeTool()
        mock_bc = AsyncMock()

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

    @pytest.mark.asyncio
    async def test_execute_error_no_book_button(self):
        """Test execute returns error when book button not found."""
        from src.server.browser.stages.finalize import BookHotelFinalizeTool

        tool = BookHotelFinalizeTool()
        mock_bc = AsyncMock()
        mock_bc.evaluate_script = AsyncMock(return_value=False)

        result = await tool.execute(mock_bc, {})

        assert result.action == StageAction.ERROR
        assert "Could not find" in result.error
