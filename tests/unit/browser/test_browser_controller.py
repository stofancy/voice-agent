"""
Unit tests for BrowserController.
"""

import pytest
from src.server.browser.browser_controller import (
    BrowserController,
    BrowserControllerConfig,
    PageInfo,
    SnapshotResult,
    ScreenshotResult,
    DEFAULT_MAX_RETRIES,
)


class TestBrowserControllerConfig:
    """Tests for BrowserControllerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserControllerConfig()
        assert config.chrome_url == "http://127.0.0.1:9222"
        assert config.chrome_profile == "voice-agent"
        assert config.timeout_seconds == 30.0
        assert "chrome-devtools-mcp" in config.mcp_args[0]

    def test_custom_config(self):
        """Test custom configuration."""
        config = BrowserControllerConfig(
            chrome_url="http://localhost:9222",
            timeout_seconds=60.0,
        )
        assert config.chrome_url == "http://localhost:9222"
        assert config.timeout_seconds == 60.0


class TestBrowserControllerInit:
    """Tests for BrowserController initialization."""

    def test_default_init(self):
        """Test default initialization."""
        bc = BrowserController()
        assert bc._client_session is None
        assert bc._current_page_id is None
        assert bc._screenshot_counter == 0

    def test_config_init(self):
        """Test initialization with custom config."""
        config = BrowserControllerConfig(chrome_url="http://localhost:9222")
        bc = BrowserController(config)
        assert bc.config.chrome_url == "http://localhost:9222"


class TestPageInfo:
    """Tests for PageInfo dataclass."""

    def test_page_info_creation(self):
        """Test PageInfo creation."""
        page = PageInfo(page_id=1, url="https://example.com", title="Example")
        assert page.page_id == 1
        assert page.url == "https://example.com"
        assert page.title == "Example"


class TestSnapshotResult:
    """Tests for SnapshotResult dataclass."""

    def test_snapshot_result_defaults(self):
        """Test SnapshotResult with defaults."""
        result = SnapshotResult(text="test")
        assert result.text == "test"
        assert result.file_path is None
        assert result.page_id is None

    def test_snapshot_result_full(self):
        """Test SnapshotResult with all fields."""
        result = SnapshotResult(
            text="test",
            file_path="/tmp/snapshot.txt",
            page_id=1,
        )
        assert result.text == "test"
        assert result.file_path == "/tmp/snapshot.txt"
        assert result.page_id == 1


class TestScreenshotResult:
    """Tests for ScreenshotResult dataclass."""

    def test_screenshot_result_defaults(self):
        """Test ScreenshotResult with defaults."""
        result = ScreenshotResult(data=b"png_data")
        assert result.data == b"png_data"
        assert result.format == "png"
        assert result.page_id is None

    def test_screenshot_result_full(self):
        """Test ScreenshotResult with all fields."""
        result = ScreenshotResult(
            data=b"jpeg_data",
            format="jpeg",
            page_id=1,
        )
        assert result.data == b"jpeg_data"
        assert result.format == "jpeg"
        assert result.page_id == 1


class TestRetryConstants:
    """Tests for retry configuration constants."""

    def test_default_max_retries(self):
        """Test default max retries value."""
        assert DEFAULT_MAX_RETRIES == 3
