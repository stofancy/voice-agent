# Implementation Plan: Browser Booking Automation

**Branch**: `003-browser-booking-automation` | **Date**: 2026-03-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/speckit.spec` output

## Summary

Enable voice-controlled hotel booking on Booking.com via Chrome DevTools MCP. Users speak Chinese commands to search hotels, select rooms, provide guest info, and reach the payment page. The system automates browser interactions while leaving payment completion to the user (FR-010).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Chrome DevTools MCP (`mcp>=1.26.0`), LangChain tools (`langchain>=0.1.0`), httpx (async HTTP), Chrome browser with remote debugging
**Storage**: In-memory `TurnContext` for session state; no persistent database required
**Testing**: pytest with pytest-asyncio
**Target Platform**: Linux/macOS server with Chrome installed
**Project Type**: Backend service module (`src/server/browser/`)
**Performance Goals**: 60s search to results (SC-001), 30s browser operation timeout (FR-014)
**Constraints**: No payment data storage (SC-007); manual payment completion only (FR-010)
**Scale/Scope**: Single user per session; 7-stage sequential flow

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Single Responsibility | ✅ PASS | BrowserController handles CDP; each StageTool has one stage |
| II. Test-First (NON-NEGOTIABLE) | ⚠️ GATE | Implementation must include unit tests before stage tools |
| III. Streaming-First | ✅ PASS | Not applicable - browser automation is request-response |
| IV. WebSocket State Machine | N/A | Different concern - browser session separate from voice WS |
| V. Observability | ✅ PASS | Structured logging via loguru; action logging required (FR-016) |

**GATE Status**: Phase 0 can proceed; Phase 1 design must ensure test infrastructure exists

## Project Structure

### Documentation (this feature)

```text
specs/003-browser-booking-automation/
├── plan.md              # This file
├── research.md          # Phase 0 output (NEEDS GENERATION)
├── data-model.md        # Phase 1 output (NEEDS GENERATION)
├── quickstart.md        # Phase 1 output (NEEDS GENERATION)
├── contracts/           # Phase 1 output (NEEDS GENERATION)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/server/
├── browser/                    # NEW: Browser automation module
│   ├── __init__.py
│   ├── browser_controller.py   # Chrome DevTools MCP wrapper
│   ├── exceptions.py           # BrowserError hierarchy
│   ├── stages/                 # 7 booking stage tools
│   │   ├── __init__.py
│   │   ├── base.py             # BookingStage, StageResult, TurnContext
│   │   ├── search.py           # Stage 1: Hotel search
│   │   ├── select_hotel.py     # Stage 2: Hotel selection
│   │   ├── navigate_property.py # Stage 3: Property page navigation
│   │   ├── select_room.py      # Stage 4: Room selection
│   │   ├── confirm_selection.py # Stage 5: Confirmation
│   │   ├── fill_guest.py       # Stage 6: Guest info
│   │   └── finalize.py         # Stage 7: Payment handoff
│   └── demo.py                 # Demo script
└── agent/
    └── tools/
        └── hotel_tool.py       # EXISTING - mock implementation

tests/
├── unit/
│   └── browser/                # NEW: Unit tests for browser module
│       ├── __init__.py
│       ├── test_browser_controller.py
│       ├── test_stages.py
│       └── test_turn_context.py
└── integration/
    └── browser/                # NEW: Integration tests
        └── test_booking_flow.py
```

**Structure Decision**: Single module `src/server/browser/` with stages subpackage. Integration with existing `src/server/agent/tools/hotel_tool.py` via LangChain tool interface.

## Phase 0: Research

### Research Tasks

| Task | Description | Status |
|------|-------------|--------|
| R1 | Chrome DevTools MCP Python SDK usage patterns | COMPLETED (exploration phase) |
| R2 | A11Y tree data extraction from Booking.com | COMPLETED (exploration phase) |
| R3 | MCP stdio transport implementation | NEEDS RESEARCH |
| R4 | Chrome CDP HTTP vs WebSocket transport | NEEDS RESEARCH |

### Key Findings from Exploration (P0)

| Finding | Source | Status |
|---------|--------|--------|
| Chrome DevTools MCP provides `list_pages`, `navigate_page`, `take_snapshot`, `take_screenshot`, `click`, `fill` | Exploration | ✅ Verified |
| A11Y tree contains full hotel data (name, price, score, location) | Exploration | ✅ Verified |
| Snapshot output ~180KB requires file-based extraction | Exploration | ✅ Verified |
| Prices only appear after date selection | Exploration | ✅ Verified |
| Consent popup: checkbox "Select all" → button "Agree" | Exploration | ✅ Verified |
| Login detection: check DOM for "Sign in" links + `bkng` cookie | Exploration | ✅ Verified |

### Remaining Unknowns

| Unknown | Impact | Resolution Approach |
|---------|--------|---------------------|
| MCP stdio process lifecycle management | HIGH | Use asyncio.create_subprocess_exec with proper cleanup |
| CDP WebSocket vs HTTP transport for evaluate_script | MEDIUM | HTTP sufficient for evaluate_script; WebSocket for events |

**Output**: `research.md` - Generated from exploration findings

## Phase 1: Design & Contracts

### Data Model (data-model.md)

| Entity | Fields | Relationships |
|--------|--------|---------------|
| BookingSession | session_id, current_stage, selected_hotel, selected_room, guest_info, created_at, updated_at | Owns TurnContext |
| HotelOption | id, name, price, score, location, url | Contained in BookingSession |
| RoomOption | id, name, price, max_guests, bed_type | Contained in BookingSession |
| StageResult | stage_name, action, data, message, options, error | Returned by stage tools |
| TurnContext | session_id, stage_index, booking_data, user_inputs, errors, selected_items | Attached to async task |

### Interface Contracts (contracts/)

| Contract | Type | Description |
|----------|------|-------------|
| BrowserController | Python class | `connect()`, `disconnect()`, `navigate(url)`, `evaluate_script(js)`, `take_snapshot()`, `extract_hotel_data()` |
| BookingStage | ABC | `execute(controller, context) -> StageResult` |
| StageResult | Dataclass | `{stage, action: StageAction, data, message, options, error}` |

### Agent Context Update

Run: `.specify/scripts/bash/update-agent-context.sh claude`

---

## Complexity Tracking

> Not applicable - no constitution violations

## Next Steps

1. **Phase 0 complete** - Research findings documented
2. **Phase 1**: Generate `data-model.md`, `contracts/`, `quickstart.md`
3. **Phase 2** (via `/speckit.tasks`): Generate `tasks.md` with implementation tasks
