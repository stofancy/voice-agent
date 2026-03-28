# Contract: BrowserController

**Type**: Python Class Interface
**Module**: `src.server.browser.browser_controller`
**Status**: Required

## Interface

```python
class BrowserController:
    def __init__(self, config: BrowserControllerConfig | None = None) -> None:
        """
        Initialize with optional configuration.
        """

    async def connect(self) -> None:
        """
        Connect to Chrome DevTools MCP server.
        Raises: BrowserError if connection fails
        """

    async def disconnect(self) -> None:
        """
        Disconnect and cleanup.
        """

    async def list_pages(self) -> list[PageInfo]:
        """
        List all open browser tabs.
        Returns: List of PageInfo(page_id, url, title)
        """

    async def new_page(self, url: str) -> PageInfo:
        """
        Open new tab and navigate to URL.
        Returns: PageInfo for new tab
        """

    async def navigate(self, url: str) -> None:
        """
        Navigate current page to URL.
        Raises: NavigationError if navigation fails
        """

    async def evaluate_script(self, script: str) -> Any:
        """
        Execute JavaScript on current page.
        Returns: Parsed result from script
        Raises: BrowserError if execution fails
        """

    async def take_snapshot(self, file_path: str | None = None) -> SnapshotResult:
        """
        Take A11Y tree snapshot of current page.
        Returns: SnapshotResult(text, file_path, page_id)
        Raises: BrowserError if snapshot fails
        """

    async def take_screenshot(self, file_path: str | None = None, full_page: bool = False) -> ScreenshotResult:
        """
        Capture screenshot of current page.
        Returns: ScreenshotResult(data, format, page_id)
        """

    async def extract_hotel_data(self) -> list[dict]:
        """
        Extract hotels from current search results page.
        Returns: List of hotel dicts with name, price, score, location, url
        """

    async def check_login_status(self) -> dict:
        """
        Check if user is logged into Booking.com.
        Returns: dict with hasSignIn, hasRegister, hasBookingSession
        """

    async def click(self, selector: str | None = None, **kwargs) -> None:
        """
        Click element by CSS selector or text.
        """

    async def fill(self, selector: str, value: str) -> None:
        """
        Fill input field by selector.
        """

    async def wait_for(self, text: str, timeout_seconds: float = 10.0) -> bool:
        """
        Wait for text to appear on page.
        Returns: True if text found, False otherwise
        """
```

## Configuration

```python
@dataclass
class BrowserControllerConfig:
    chrome_url: str = "http://127.0.0.1:9222"
    chrome_profile: str = "voice-agent"
    mcp_command: str = "npx"
    mcp_args: list[str] = ["chrome-devtools-mcp", "--browserUrl", "http://127.0.0.1:9222"]
    timeout_seconds: float = 30.0
    screenshot_dir: str | None = None
```

## Exceptions

| Exception | Raised When |
|-----------|-------------|
| BrowserError | Base exception |
| NavigationError | Page navigation fails |
| ElementNotFoundError | Element not found for click/fill |
| PopupBlockedError | Popup blocks interaction |
| ScreenshotError | Screenshot capture fails |

## Usage Example

```python
config = BrowserControllerConfig()
bc = BrowserController(config)

await bc.connect()
await bc.navigate("https://www.booking.com")
hotels = await bc.extract_hotel_data()
await bc.disconnect()
```
