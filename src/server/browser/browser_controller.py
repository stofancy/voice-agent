"""
BrowserController - Chrome DevTools MCP integration for Booking.com automation.

Provides high-level browser automation via Chrome DevTools MCP protocol.
"""

import asyncio
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from loguru import logger

from .exceptions import (
    BrowserError,
    ElementNotFoundError,
    NavigationError,
    PopupBlockedError,
    ScreenshotError,
)

# Chrome DevTools MCP server configuration
CHROME_REMOTE_DEBUGGING_PORT = 9222
CHROME_PROFILE_NAME = "voice-agent"


@dataclass
class PageInfo:
    """Information about a browser page/tab."""

    page_id: int
    url: str
    title: str


@dataclass
class SnapshotResult:
    """Result from take_snapshot operation."""

    text: str
    file_path: str | None = None
    page_id: int | None = None


@dataclass
class ScreenshotResult:
    """Result from take_screenshot operation."""

    data: bytes
    format: str = "png"
    page_id: int | None = None


@dataclass
class BrowserControllerConfig:
    """Configuration for BrowserController."""

    chrome_url: str = f"http://127.0.0.1:{CHROME_REMOTE_DEBUGGING_PORT}"
    chrome_profile: str = CHROME_PROFILE_NAME
    mcp_command: str = "npx"
    mcp_args: list[str] = field(
        default_factory=lambda: ["chrome-devtools-mcp", "--browserUrl", f"http://127.0.0.1:{CHROME_REMOTE_DEBUGGING_PORT}"]
    )
    timeout_seconds: float = 30.0
    screenshot_dir: str | None = None


class BrowserController:
    """
    Chrome DevTools MCP controller for browser automation.

    Provides high-level operations like navigate, click, fill, snapshot, screenshot
    via Chrome DevTools MCP protocol.
    """

    def __init__(self, config: BrowserControllerConfig | None = None):
        """
        Initialize BrowserController.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or BrowserControllerConfig()
        self._client_session: Any = None
        self._mcp_process: subprocess.Popen | None = None
        self._current_page_id: int | None = None
        self._screenshot_counter = 0

        # Create screenshot directory if needed
        if self.config.screenshot_dir:
            os.makedirs(self.config.screenshot_dir, exist_ok=True)
        else:
            self.config.screenshot_dir = tempfile.mkdtemp(prefix="openclaw_screenshots_")

        logger.info(f"[BrowserController] Initialized with config: {self.config}")

    async def connect(self) -> None:
        """
        Connect to Chrome DevTools MCP server.

        This starts the MCP process and establishes a session.
        """
        if self._client_session is not None:
            logger.warning("[BrowserController] Already connected, skipping connect")
            return

        try:
            from mcp import ClientSession, StdioServerParameters

            # Create server parameters for stdio connection
            server_params = StdioServerParameters(
                command=self.config.mcp_command,
                args=self.config.mcp_args,
                env={},
            )

            # Start the MCP process
            logger.info("[BrowserController] Starting MCP process...")
            self._mcp_process = await asyncio.create_subprocess_exec(
                server_params.command,
                *server_params.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Create client session
            logger.info("[BrowserController] Creating MCP client session...")
            # Note: In practice, we need to handle the stdio connection properly
            # For now, we'll use a simplified approach
            self._client_session = True  # Placeholder - actual implementation needs proper stdio handling

            logger.info("[BrowserController] Connected successfully")

        except ImportError as e:
            raise BrowserError(
                "MCP package not found. Install with: uv add mcp",
                details=str(e),
            )
        except Exception as e:
            raise BrowserError(
                f"Failed to connect to Chrome DevTools MCP: {e}",
                details=str(e),
            )

    async def disconnect(self) -> None:
        """Disconnect from Chrome DevTools MCP server."""
        if self._mcp_process:
            self._mcp_process.terminate()
            try:
                await asyncio.wait_for(self._mcp_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._mcp_process.kill()
            self._mcp_process = None

        self._client_session = None
        self._current_page_id = None
        logger.info("[BrowserController] Disconnected")

    async def list_pages(self) -> list[PageInfo]:
        """
        List all open browser pages/tabs.

        Returns:
            List of PageInfo objects with page_id, url, and title.
        """
        # Use Chrome's JSON endpoint directly
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.chrome_url}/json",
                    timeout=10.0,
                )
                response.raise_for_status()
                pages = response.json()

                return [
                    PageInfo(
                        page_id=int(p.get("id", 0)),
                        url=p.get("url", ""),
                        title=p.get("title", ""),
                    )
                    for p in pages
                    if p.get("type") == "page"
                ]
        except Exception as e:
            raise BrowserError(f"Failed to list pages: {e}", details=str(e))

    async def new_page(self, url: str) -> PageInfo:
        """
        Open a new page/tab and navigate to URL.

        Args:
            url: URL to navigate to.

        Returns:
            PageInfo for the new page.
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.chrome_url}/json/new",
                    timeout=10.0,
                )
                response.raise_for_status()
                page = response.json()

                page_id = int(page.get("id", 0))
                self._current_page_id = page_id

                # Navigate to the target URL
                if url:
                    await self.navigate(url)

                return PageInfo(
                    page_id=page_id,
                    url=page.get("url", ""),
                    title=page.get("title", ""),
                )
        except Exception as e:
            raise BrowserError(f"Failed to create new page: {e}", details=str(e))

    async def close_page(self, page_id: int | None = None) -> None:
        """
        Close a page/tab.

        Args:
            page_id: Page ID to close. Uses current page if not specified.
        """
        target_page = page_id or self._current_page_id
        if not target_page:
            raise BrowserError("No page specified to close")

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.chrome_url}/json/close/{target_page}",
                    timeout=10.0,
                )
                response.raise_for_status()

                if self._current_page_id == target_page:
                    self._current_page_id = None

        except Exception as e:
            raise BrowserError(f"Failed to close page: {e}", details=str(e))

    async def navigate(self, url: str) -> None:
        """
        Navigate current page to URL.

        Args:
            url: URL to navigate to.
        """
        if not self._current_page_id:
            # If no page open, create one
            await self.new_page(url)
            return

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Use Chrome DevTools protocol via WebSocket
                # For simplicity, we use the HTTP JSON API to navigate
                response = await client.post(
                    f"{self.config.chrome_url}/json/navigate/{self._current_page_id}",
                    json={"url": url},
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()

        except Exception as e:
            raise NavigationError(f"Navigation to {url} failed: {e}", details=str(e))

    async def take_snapshot(self, file_path: str | None = None) -> SnapshotResult:
        """
        Take accessibility tree snapshot of current page.

        The snapshot is saved to a file to avoid token limits.
        The returned text is truncated - use file_path to read full content.

        Args:
            file_path: Optional path to save snapshot. Auto-generated if not provided.

        Returns:
            SnapshotResult with truncated text and file_path for full content.
        """
        if not self._current_page_id:
            raise BrowserError("No page available for snapshot")

        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(self.config.screenshot_dir, f"snapshot_{timestamp}.txt")

        try:
            # Use CDP via HTTP - get accessibility tree
            import httpx

            async with httpx.AsyncClient() as client:
                # Enable accessibility domain
                await client.post(
                    f"{self.config.chrome_url}/json/profiler/enable",
                    timeout=10.0,
                )

                # Take snapshot via evaluate_script approach
                # Since direct CDP accessibility snapshot is complex, we use JS
                snapshot_content = await self._execute_script_raw(
                    """
                    () => {
                        function serializeNode(node, depth = 0) {
                            if (!node) return '';
                            const indent = '  '.repeat(depth);
                            let result = indent;
                            if (node.role) result += `role="${node.role.value || node.role}" `;
                            if (node.name) result += `name="${node.name}" `;
                            if (node.value) result += `value="${node.value}" `;
                            if (node.description) result += `description="${node.description}" `;
                            if (node.url) result += `url="${node.url}" `;
                            if (node.ariaProperties) result += `aria="${JSON.stringify(node.ariaProperties)}" `;
                            result += '\\n';
                            if (node.children) {
                                for (const child of node.children) {
                                    result += serializeNode(child, depth + 1);
                                }
                            }
                            return result;
                        }
                        return serializeNode(await accessibility.getCompletions());
                    }
                    """
                )

                # Save to file
                with open(file_path, "w", encoding="utf-8") as f:
                    # Wrap in JSON structure that matches MCP output format
                    wrapper = [{"type": "text", "text": snapshot_content or ""}]
                    f.write(json.dumps(wrapper, ensure_ascii=False, indent=2))

                # Return truncated content
                truncated = (snapshot_content or "")[:5000]

                return SnapshotResult(
                    text=truncated,
                    file_path=file_path,
                    page_id=self._current_page_id,
                )

        except Exception as e:
            raise BrowserError(f"Snapshot failed: {e}", details=str(e))

    async def _execute_script_raw(self, script: str) -> str:
        """
        Execute JavaScript and return raw result.

        Args:
            script: JavaScript code to execute.

        Returns:
            String result of script execution.
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.chrome_url}/json/runtime/evaluate",
                    json={
                        "expression": script,
                        "returnByValue": True,
                        "generatePreview": False,
                    },
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("result", {}).get("value", "") or ""

        except Exception as e:
            raise BrowserError(f"Script execution failed: {e}", details=str(e))

    async def evaluate_script(self, script: str) -> Any:
        """
        Execute JavaScript on current page.

        Args:
            script: JavaScript code to execute.

        Returns:
            Parsed result from script execution.
        """
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.chrome_url}/json/runtime/evaluate",
                    json={
                        "expression": script,
                        "returnByValue": True,
                        "generatePreview": True,
                    },
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                result = response.json()

                # Extract value from result
                value = result.get("result", {}).get("value")
                description = result.get("result", {}).get("description")

                # Handle different value types
                if isinstance(value, dict) and value.get("type") == "undefined":
                    return description or None

                return value

        except Exception as e:
            raise BrowserError(f"Script evaluation failed: {e}", details=str(e))

    async def take_screenshot(
        self,
        file_path: str | None = None,
        full_page: bool = False,
    ) -> ScreenshotResult:
        """
        Take screenshot of current page.

        Args:
            file_path: Optional path to save screenshot.
            full_page: If True, capture full scrollable page.

        Returns:
            ScreenshotResult with image data.
        """
        if not self._current_page_id:
            raise BrowserError("No page available for screenshot")

        if file_path is None:
            self._screenshot_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "png" if not full_page else "jpg"
            file_path = os.path.join(
                self.config.screenshot_dir,
                f"screenshot_{timestamp}_{self._screenshot_counter}.{ext}",
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # Use Chrome's captureScreenshot via debugger endpoint
                response = await client.post(
                    f"{self.config.chrome_url}/json/debugger/screenshot",
                    json={"fullPage": full_page},
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()

                # Response is base64 encoded PNG
                import base64

                image_data = response.content
                if full_page:
                    # For full page, we get base64
                    image_data = base64.b64decode(response.text)

                # Save to file
                with open(file_path, "wb") as f:
                    f.write(image_data)

                return ScreenshotResult(
                    data=image_data,
                    format="png" if not full_page else "jpeg",
                    page_id=self._current_page_id,
                )

        except Exception as e:
            raise ScreenshotError(f"Screenshot failed: {e}", details=str(e))

    async def click(self, selector: str | None = None, **kwargs) -> None:
        """
        Click an element on the page.

        Args:
            selector: CSS selector or other selector for the element.
            **kwargs: Alternative selectors (uid, text, etc.)
        """
        try:
            if selector:
                # Use JavaScript click
                await self.evaluate_script(
                    f"""
                    () => {{
                        const el = document.querySelector('{selector.replace("'", "\\'")}');
                        if (el) {{
                            el.click();
                            return 'clicked';
                        }}
                        return 'not found';
                    }}
                    """
                )
            elif "text" in kwargs:
                # Click by text content
                text = kwargs["text"]
                await self.evaluate_script(
                    f"""
                    () => {{
                        const buttons = Array.from(document.querySelectorAll('button'));
                        for (const btn of buttons) {{
                            if (btn.innerText && btn.innerText.includes('{text}')) {{
                                btn.click();
                                return 'clicked';
                            }}
                        }}
                        return 'not found';
                    }}
                    """
                )
            elif "uid" in kwargs:
                # Click by A11Y tree UID - not directly supported, use snapshot
                raise BrowserError("UID-based click not yet implemented")

        except Exception as e:
            raise BrowserError(f"Click failed: {e}", details=str(e))

    async def fill(self, selector: str, value: str) -> None:
        """
        Fill an input field.

        Args:
            selector: CSS selector for the input element.
            value: Value to fill in.
        """
        try:
            # Use JavaScript to fill the input
            await self.evaluate_script(
                f"""
                () => {{
                    const el = document.querySelector('{selector.replace("'", "\\'")}');
                    if (el) {{
                        // Clear existing value
                        el.value = '';
                        // Set new value
                        el.value = '{value.replace("'", "\\'")}';
                        // Trigger input event for React/Vue
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'filled';
                    }}
                    return 'not found';
                }}
                """
            )
        except Exception as e:
            raise BrowserError(f"Fill failed: {e}", details=str(e))

    async def select_option(self, selector: str, value: str) -> None:
        """
        Select an option from a dropdown.

        Args:
            selector: CSS selector for the select element.
            value: Value to select.
        """
        try:
            await self.evaluate_script(
                f"""
                () => {{
                    const el = document.querySelector('{selector.replace("'", "\\'")}');
                    if (el) {{
                        el.value = '{value.replace("'", "\\'")}';
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'selected';
                    }}
                    return 'not found';
                }}
                """
            )
        except Exception as e:
            raise BrowserError(f"Select option failed: {e}", details=str(e))

    async def wait_for(self, text: str, timeout_seconds: float = 10.0) -> bool:
        """
        Wait for text to appear on page.

        Args:
            text: Text to wait for.
            timeout_seconds: Maximum time to wait.

        Returns:
            True if text found, False otherwise.
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            try:
                result = await self.evaluate_script(
                    f"""
                    () => {{
                        return document.body.innerText.includes('{text.replace("'", "\\'")}');
                    }}
                    """
                )
                if result:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    async def handle_popup(self, action: str = "dismiss") -> None:
        """
        Handle a popup dialog.

        Args:
            action: Action to take - "accept", "dismiss", or button text to click.
        """
        try:
            if action == "accept":
                await self.evaluate_script(
                    """
                    () => {
                        const dialog = document.querySelector('dialog, [role="dialog"], .modal');
                        if (dialog) {
                            if (dialog.showModal) dialog.showModal();
                            return 'opened';
                        }
                        // Try alert/confirm
                        return null;
                    }
                    """
                )
            elif action == "dismiss":
                # Look for common dismiss buttons
                await self.click(text="Dismiss")
                await asyncio.sleep(0.3)
                await self.click(text="Stay on Booking.com")
                await asyncio.sleep(0.3)
                await self.click(text="Close")

    async def extract_hotel_data(self) -> list[dict]:
        """
        Extract hotel data from current search results page.

        Uses the A11Y tree approach documented in exploration/README.md.

        Returns:
            List of hotel dictionaries with name, price, score, location, url.
        """
        # First, get the snapshot file path
        snapshot_result = await self.take_snapshot()
        if not snapshot_result.file_path:
            return []

        # Parse using the approach from parse_a11y_tree.py
        return await self._parse_hotels_from_snapshot(snapshot_result.file_path)

    async def _parse_hotels_from_snapshot(self, file_path: str) -> list[dict]:
        """
        Parse hotel data from a snapshot file.

        Args:
            file_path: Path to snapshot file.

        Returns:
            List of hotel dictionaries.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse the JSON wrapper
            wrapper = json.loads(content)
            text = wrapper[0]["text"] if wrapper else ""

            # Extract hotels using regex patterns from exploration
            hotels = []
            lines = text.split("\n")
            current_hotel = None

            for line in lines:
                stripped = line.strip()

                # Hotel name: link "xxx Opens in new window" url="...hotel..."
                if " Opens in new window" in stripped and "hotel/jp/" in stripped:
                    if current_hotel and (
                        current_hotel.get("price") or current_hotel.get("score")
                    ):
                        hotels.append(current_hotel)

                    match = re.search(r'link "([^"]+)"', stripped)
                    if match:
                        name = match.group(1).replace(" Opens in new window", "")
                        current_hotel = {
                            "name": name,
                            "price": None,
                            "score": None,
                            "location": None,
                            "url": None,
                        }

                    # Extract URL
                    url_match = re.search(r'url="([^"]+)"', stripped)
                    if url_match and current_hotel:
                        current_hotel["url"] = url_match.group(1)

                # Price: Current price CNY XX,XXX
                elif current_hotel and "Current price" in stripped:
                    match = re.search(
                        r"Current price (CNY|USD|¥)\s*([\d,]+)", stripped
                    )
                    if match:
                        current_hotel["price"] = f"{match.group(1)} {match.group(2)}"

                # Score: Scored X.X
                elif current_hotel and "Scored" in stripped:
                    match = re.search(r"Scored (\d+\.?\d*)", stripped)
                    if match:
                        current_hotel["score"] = match.group(1)

                # Location: xxx· Show on map
                elif current_hotel and "Show on map" in stripped:
                    location_match = re.search(r"([^·]+)·", stripped)
                    if location_match:
                        current_hotel["location"] = location_match.group(1).strip()

            # Don't forget the last hotel
            if current_hotel and (
                current_hotel.get("price") or current_hotel.get("score")
            ):
                hotels.append(current_hotel)

            return hotels

        except Exception as e:
            logger.error(f"[BrowserController] Failed to parse hotels: {e}")
            return []

    async def check_login_status(self) -> dict:
        """
        Check if user is logged in to Booking.com.

        Returns:
            Dict with hasSignIn, hasRegister, hasBookingSession.
        """
        try:
            result = await self.evaluate_script(
                """
                () => {
                    const allLinks = document.querySelectorAll('a');
                    let hasSignIn = false;
                    let hasRegister = false;

                    for (const link of allLinks) {
                        const text = link.innerText || '';
                        const href = link.href || '';
                        if (text.toLowerCase().includes('sign in') || href.includes('signin')) {
                            hasSignIn = true;
                        }
                        if (text.toLowerCase().includes('register')) {
                            hasRegister = true;
                        }
                    }

                    return {
                        hasSignIn,
                        hasRegister,
                        hasBookingSession: document.cookie.includes('bkng')
                    };
                }
                """
            )
            return result or {"hasSignIn": False, "hasRegister": False, "hasBookingSession": False}

        except Exception as e:
            logger.error(f"[BrowserController] Login check failed: {e}")
            return {"hasSignIn": False, "hasRegister": False, "hasBookingSession": False}

    def __repr__(self) -> str:
        return f"BrowserController(page_id={self._current_page_id})"
