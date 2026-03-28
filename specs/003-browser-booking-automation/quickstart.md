# Quickstart: Browser Booking Automation

**Branch**: `003-browser-booking-automation`
**Date**: 2026-03-28

## Prerequisites

1. **Chrome browser** installed on the system
2. **Python 3.10+** with `uv` package manager
3. **MCP package**: `uv add mcp>=1.26.0`

## Setup

### 1. Start Chrome with Remote Debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome/voice-agent"

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.config/google-chrome/voice-agent"
```

Or use an existing Chrome profile by navigating to:
`chrome://inspect` and note the debugging port.

### 2. Verify Chrome Connection

```python
import httpx

async def check_chrome():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://127.0.0.1:9222/json")
        pages = response.json()
        print(f"Open pages: {len(pages)}")
        for p in pages:
            print(f"  - {p.get('title', 'No title')}")

import asyncio
asyncio.run(check_chrome())
```

### 3. Install Dependencies

```bash
cd /path/to/voice-agent
uv add mcp>=1.26.0
```

## Basic Usage

### Initialize BrowserController

```python
from src.server.browser import BrowserController, BrowserControllerConfig

config = BrowserControllerConfig(
    chrome_url="http://127.0.0.1:9222",
    timeout_seconds=30.0,
)

bc = BrowserController(config)
await bc.connect()
```

### Perform Hotel Search

```python
from src.server.browser.stages import BookHotelSearchTool

search_tool = BookHotelSearchTool()
context = {
    "location": "Tokyo",
    "checkin": "2026-04-01",
    "checkout": "2026-04-05",
    "guests": 2,
    "rooms": 1,
}

result = await search_tool.execute(bc, context)
print(f"Action: {result.action}")
print(f"Message: {result.message}")
```

### Extract Hotels from Results

```python
from src.server.browser.stages import BookHotelSelectHotelTool

select_tool = BookHotelSelectHotelTool()
result = await select_tool.execute(bc, context)

if result.action == StageAction.WAIT_FOR_SELECTION:
    for opt in result.options:
        print(f"{opt['index']}. {opt['display']}")
```

### Select Hotel and Proceed

```python
# User selects option 1
context["selected_hotel"] = result.options[0]["details"]

from src.server.browser.stages import BookHotelNavigatePropertyTool

nav_tool = BookHotelNavigatePropertyTool()
result = await nav_tool.execute(bc, context)
# Now on hotel property page
```

### Cleanup

```python
await bc.disconnect()
```

## Demo Script

Run the demo without real browser interaction:

```bash
cd /path/to/voice-agent
python -m src.server.browser.demo
```

This demonstrates the stage flow with mock data.

## Testing

### Run Unit Tests

```bash
cd /path/to/voice-agent
.venv/bin/python -m pytest tests/unit/browser/ -v
```

### Run Integration Tests

```bash
# Requires Chrome running with remote debugging
.venv/bin/python -m pytest tests/integration/browser/ -v
```

## Troubleshooting

### Chrome Not Starting

```
Error: Chrome failed to start
```

- Ensure Chrome is not already running with different profile
- Try a different `--user-data-dir`
- Check if port 9222 is available

### Connection Refused

```
httpx.ConnectError: [Errno 111] Connection refused
```

- Verify Chrome started with `--remote-debugging-port=9222`
- Check firewall settings
- Try `curl http://127.0.0.1:9222/json`

### Element Not Found

```
ElementNotFoundError: Could not find element
```

- Page may not have loaded fully
- Check if popup is blocking
- Verify selector is correct

### A11Y Snapshot Empty

```
No hotels extracted
```

- Ensure dates are selected (prices only appear with dates)
- Try navigating with URL params: `?checkin=2026-04-01&checkout=2026-04-05`
- Verify page has search results

## Next Steps

1. **Review** `data-model.md` for entity definitions
2. **Review** `contracts/` for interface specifications
3. **Generate tasks** via `/speckit.tasks`
4. **Implement** following the constitution's test-first principle
