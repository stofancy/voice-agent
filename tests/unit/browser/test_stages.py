"""
Unit tests for booking stage tools.
"""

import pytest
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
