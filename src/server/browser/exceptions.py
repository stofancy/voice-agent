"""
Browser automation exceptions.
"""


class BrowserError(Exception):
    """Base exception for browser automation errors."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.details = details


class NavigationError(BrowserError):
    """Raised when page navigation fails."""

    pass


class ElementNotFoundError(BrowserError):
    """Raised when an element cannot be found on the page."""

    pass


class PopupBlockedError(BrowserError):
    """Raised when a popup blocks interaction."""

    pass


class ScreenshotError(BrowserError):
    """Raised when screenshot capture fails."""

    pass
