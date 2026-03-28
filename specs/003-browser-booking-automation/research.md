# Research: Browser Booking Automation

**Branch**: `003-browser-booking-automation`
**Date**: 2026-03-28
**Status**: Complete

## Chrome DevTools MCP Integration

### Decision: Use Python MCP SDK with stdio transport

**Rationale**: The MCP Python SDK (`mcp>=1.26.0`) provides `ClientSession` with `StdioServerParameters`. Chrome DevTools MCP runs as a separate process (`npx chrome-devtools-mcp`), communicated via stdio.

**Alternatives Considered**:
- Direct CDP WebSocket: More complex, requires CDP protocol parsing
- HTTP Debugging Protocol: Limited to Chrome's built-in endpoints only

### Chrome CDP Access Pattern

Chrome exposes debugging via:
1. **HTTP JSON API**: `http://127.0.0.1:9222/json/` - page listing, navigation
2. **WebSocket CDP**: Full debugging protocol - evaluate_script, DOM access

For this implementation, we use:
- HTTP JSON API for page management (`list_pages`, `new_page`, `navigate`)
- HTTP POST for `runtime/evaluate` (evaluate_script equivalent)
- CDP accessibility snapshot via `accessibility.getCompletions()`

### Chrome Launch Configuration

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=~/Library/Application\ Support/Google/Chrome/voice-agent
```

## A11Y Tree Data Extraction

### Decision: Use A11Y tree snapshot + Python file parser

**Rationale**: `take_snapshot` returns ~180KB accessibility tree containing full semantic data. Direct DOM queries fail due to dynamic class names. A11Y tree provides stable semantic structure.

**Pattern for hotel extraction**:
```
Hotel name: link "xxx Opens in new window" url="...hotel..."
Score: Scored 8.8 Excellent 2,230 reviews
Price: Current price CNY 12,123
Location: xxx· Show on map
```

### Python Parser Approach

```python
def extract_hotels(text: str) -> list[dict]:
    hotels = []
    current = None
    for line in text.split('\n'):
        if ' Opens in new window' in line and 'hotel/jp/' in line:
            # New hotel entry
            current = {'name': extract_name(line), 'price': None, ...}
        elif current and 'Current price' in line:
            current['price'] = extract_price(line)
        elif current and 'Scored' in line:
            current['score'] = extract_score(line)
    return hotels
```

## Booking.com Flow

### 7-Stage Flow

| Stage | Page | Key Actions |
|-------|------|-------------|
| 1. Search | Home | Fill destination, dates, guests → Search |
| 2. Results | searchresults.html | Extract hotels → Wait for selection |
| 3. Property | hotel page | Navigate to hotel → Dismiss popups |
| 4. Room | hotel page | Extract rooms → Wait for selection |
| 5. Confirm | summary | Show summary → Wait for confirmation |
| 6. Guest | checkout | Fill name, email |
| 7. Finalize | payment | Click Book → Handoff |

### Popup Handling

| Popup | Detection | Action |
|-------|-----------|--------|
| Consent | Checkbox "Select all" | Click → Click "Accept" |
| Genius discount | "Dismiss" button | Click Dismiss |
| Login required | "Sign in" links visible | Prompt user |

### Price Display

- **Prerequisite**: Dates must be selected before prices appear
- **Solution**: Navigate with URL params `?checkin=2026-04-01&checkout=2026-04-05`

## Error Handling

### Timeout Strategy

| Operation | Timeout | Retry |
|-----------|---------|-------|
| Page navigation | 30s | 3x |
| Element click | 10s | 3x |
| Script evaluation | 30s | 3x |
| Snapshot extraction | 60s | 2x |

### Exception Hierarchy

```
BrowserError (base)
├── NavigationError
├── ElementNotFoundError
├── PopupBlockedError
└── ScreenshotError
```

## MCP Token Limit Handling

**Problem**: `take_snapshot` output ~180KB exceeds MCP tool token limit (~25K)

**Solution**:
1. Save snapshot to file (auto-generated path in `/tmp/openclaw_screenshots/`)
2. Python parser reads file directly
3. Return truncated preview + file_path for full access

## Alternatives Rejected

| Alternative | Rejected Because |
|-------------|------------------|
| DOM-based extraction | Dynamic class names, fragile |
| Screenshot + OCR | Slow, error-prone for text |
| Booking.com API | Not publicly available |
| Selenium/Playwright | Heavy, no MCP integration |
