# Tasks: Browser Booking Automation

**Feature**: Browser Booking Automation
**Branch**: `003-browser-booking-automation`
**Created**: 2026-03-28
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Overview

| Metric | Value |
|--------|-------|
| Total Tasks | 28 |
| User Stories | 4 |
| MVP Scope | User Story 1 (Tasks T001-T010) |

## Task Count by User Story

| User Story | Tasks | Description |
|------------|-------|-------------|
| Setup | T001-T002 | Project initialization |
| Foundational | T003-T008 | Core infrastructure |
| US1 (Search & Select) | T009-T014 | Hotel search and selection |
| US2 (Room & Guest) | T015-T020 | Room selection and guest info |
| US3 (Payment Handoff) | T021-T024 | Confirmation and finalize |
| US4 (Session Recovery) | T025-T026 | Pause/resume and retry |
| Polish | T027-T028 | Integration tests and demo |

## Implementation Strategy

**MVP Scope**: User Story 1 (T001-T014) - Complete hotel search and selection flow
**Delivery**: Incremental per user story; each story is independently testable

---

## Phase 1: Setup

### Goal
Initialize project structure and dependencies.

### Tasks

- [ ] T001 Create browser module directory structure in `src/server/browser/` and `tests/unit/browser/`
  - File: `src/server/browser/__init__.py`
  - File: `tests/unit/browser/__init__.py`
  - File: `tests/integration/browser/__init__.py`

- [ ] T002 Add MCP package dependency to pyproject.toml
  - File: `pyproject.toml`
  - Action: Add `mcp>=1.26.0` to dependencies

---

## Phase 2: Foundational

### Goal
Build core infrastructure required by all stage tools.

### Tasks

- [ ] T003 Implement BrowserControllerConfig dataclass
  - File: `src/server/browser/browser_controller.py`
  - Fields: chrome_url, chrome_profile, mcp_command, mcp_args, timeout_seconds, screenshot_dir

- [ ] T004 Implement exception hierarchy in `src/server/browser/exceptions.py`
  - Classes: BrowserError, NavigationError, ElementNotFoundError, PopupBlockedError, ScreenshotError

- [ ] T005 Implement PageInfo, SnapshotResult, ScreenshotResult dataclasses
  - File: `src/server/browser/browser_controller.py`
  - Used for return types from browser operations

- [ ] T006 Implement TurnContext class for session state management
  - File: `src/server/browser/stages/base.py`
  - Methods: update, get, set_selected, advance_stage, add_error

- [ ] T007 Implement BookingStage abstract base class
  - File: `src/server/browser/stages/base.py`
  - Abstract methods: description, execute
  - Base methods: should_skip

- [ ] T008 Implement StageResult dataclass and StageAction enum
  - File: `src/server/browser/stages/base.py`
  - Actions: CONTINUE, WAIT_FOR_SELECTION, WAIT_FOR_CONFIRMATION, COMPLETE, ERROR

---

## Phase 3: User Story 1 - Search & Select Hotel

**Priority**: P1 (MVP)
**Goal**: User can search hotels via voice and select one from results
**Independent Test**: "Find hotels in Tokyo for April 1-5" → Hotel options displayed → "Select second one" → Hotel selected

### Tasks

- [ ] T009 [US1] Implement BookHotelSearchTool (Stage 1)
  - File: `src/server/browser/stages/search.py`
  - Actions: Navigate to Booking.com, fill search form, submit, handle consent popup
  - Returns: StageResult with CONTINUE action

- [ ] T010 [US1] Implement consent popup handling in search stage
  - File: `src/server/browser/stages/search.py`
  - Method: _handle_consent_popup()
  - Logic: Click "Select all" checkbox → Click "Accept"

- [ ] T011 [US1] Implement BookHotelSelectHotelTool (Stage 2)
  - File: `src/server/browser/stages/select_hotel.py`
  - Actions: Extract hotels from A11Y tree, build options list
  - Returns: StageResult with WAIT_FOR_SELECTION action and hotel options

- [ ] T012 [US1] Implement A11Y tree hotel extraction parser
  - File: `src/server/browser/stages/base.py` (or separate parser module)
  - Method: _parse_hotels_from_snapshot()
  - Patterns: link with " Opens in new window", "Current price", "Scored", "Show on map"

- [ ] T013 [US1] Implement natural language selection helper
  - File: `src/server/browser/stages/select_hotel.py`
  - Method: _parse_selection()
  - Supported: "第二个", "贵一点的", "带早餐的", "评分最高的"

- [ ] T014 [US1] Write unit tests for US1 stage tools
  - File: `tests/unit/browser/test_stages.py`
  - Coverage: BookHotelSearchTool, BookHotelSelectHotelTool

---

## Phase 4: User Story 2 - Room Selection & Guest Info

**Priority**: P2
**Goal**: User can select room type and provide guest information
**Independent Test**: After hotel selection → "Choose double room" → "John Doe, john@email.com" → Ready for confirmation

### Tasks

- [ ] T015 [US2] Implement BookHotelNavigatePropertyTool (Stage 3)
  - File: `src/server/browser/stages/navigate_property.py`
  - Actions: Navigate to hotel URL, dismiss popups
  - Returns: StageResult with CONTINUE action

- [ ] T016 [US2] Implement popup dismissal for property page
  - File: `src/server/browser/stages/navigate_property.py`
  - Method: _handle_popups()
  - Popups: Genius discount, "Stay on Booking.com"

- [ ] T017 [US2] Implement BookHotelSelectRoomTool (Stage 4)
  - File: `src/server/browser/stages/select_room.py`
  - Actions: Extract room options from property page, build options list
  - Returns: StageResult with WAIT_FOR_SELECTION action

- [ ] T018 [US2] Implement room extraction from property page
  - File: `src/server/browser/stages/select_room.py`
  - Method: _extract_rooms()
  - Selectors: [data-testid="room-card"], room-name, price

- [ ] T019 [US2] Implement BookHotelFillGuestTool (Stage 6)
  - File: `src/server/browser/stages/fill_guest.py`
  - Actions: Fill guest name and email fields
  - Returns: StageResult with CONTINUE action

- [ ] T020 [US2] Write unit tests for US2 stage tools
  - File: `tests/unit/browser/test_stages.py`
  - Coverage: BookHotelNavigatePropertyTool, BookHotelSelectRoomTool, BookHotelFillGuestTool

---

## Phase 5: User Story 3 - Payment Handoff

**Priority**: P3
**Goal**: User confirms booking and reaches payment page
**Independent Test**: After guest info → "Confirm booking" → Payment page displayed

### Tasks

- [ ] T021 [US3] Implement BookHotelConfirmSelectionTool (Stage 5)
  - File: `src/server/browser/stages/confirm_selection.py`
  - Actions: Build summary, show confirmation
  - Returns: StageResult with WAIT_FOR_CONFIRMATION action

- [ ] T022 [US3] Implement confirmation message builder
  - File: `src/server/browser/stages/confirm_selection.py`
  - Method: _build_confirmation_message()
  - Format: Hotel, room, dates, guests, price

- [ ] T023 [US3] Implement BookHotelFinalizeTool (Stage 7)
  - File: `src/server/browser/stages/finalize.py`
  - Actions: Click book button, verify payment page reached
  - Returns: StageResult with COMPLETE action

- [ ] T024 [US3] Write unit tests for US3 stage tools
  - File: `tests/unit/browser/test_stages.py`
  - Coverage: BookHotelConfirmSelectionTool, BookHotelFinalizeTool

---

## Phase 6: User Story 4 - Session Management

**Priority**: P4
**Goal**: System handles interruptions and errors gracefully
**Independent Test**: Mid-booking "stop" → "continue my booking" → Resume from last stage

### Tasks

- [ ] T025 [US4] Implement session pause and resume in TurnContext
  - File: `src/server/browser/stages/base.py`
  - Methods: pause(), resume(), get_state(), restore_state()

- [ ] T026 [US4] Implement retry mechanism for browser operations
  - File: `src/server/browser/browser_controller.py`
  - Method: _execute_with_retry()
  - Config: 3 retries, exponential backoff, FR-015 compliance

---

## Phase 7: Polish & Cross-Cutting

### Goal
Complete integration and tooling.

### Tasks

- [ ] T027 Write integration test for full booking flow
  - File: `tests/integration/browser/test_booking_flow.py`
  - Coverage: End-to-end from search to payment page (mock Chrome)

- [ ] T028 Create demo script demonstrating stage flow
  - File: `src/server/browser/demo.py`
  - Mode: Mock data without real browser

---

## Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──────► T003-T008
    │                           │
    │                           ▼
    │                    Phase 3 (US1) ──────► T009-T014
    │                               │
    │                               ▼
    └────────────────────────► Phase 4 (US2) ──────► T015-T020
                                │
                                ▼
                          Phase 5 (US3) ──────► T021-T024
                                │
                                ▼
                          Phase 6 (US4) ──────► T025-T026
                                │
                                ▼
                          Phase 7 (Polish) ──────► T027-T028
```

## Parallel Execution Examples

**Example 1**: US2 stages can be implemented in parallel after foundational (T003-T008) complete:
- T015 (navigate_property) and T017 (select_room) are independent
- T019 (fill_guest) is independent of T015/T017

**Example 2**: Unit tests (T014, T020, T024) can run in parallel after respective stage implementation

---

## Independent Test Criteria

| User Story | Test Criteria |
|------------|---------------|
| US1 | Voice command "Find hotels in Tokyo for April 1-5" → Hotel list displayed → "Select second one" → Hotel selected |
| US2 | After US1 → "Choose double room" → Room options displayed → "John Doe, john@email.com" → Guest form filled |
| US3 | After US2 → "Confirm booking" → Payment page reached with message "Please complete payment manually" |
| US4 | Mid-booking "stop" → State preserved → "Continue booking" → Resume from last stage |

---

## Format Validation

- [x] All tasks follow checklist format: `- [ ] [TaskID] [Story?] Description with file path`
- [x] Task IDs are sequential (T001-T028)
- [x] User story phases have [USN] labels
- [x] Setup/Foundational/Polish phases have no story label
- [x] All file paths are explicit
- [x] Parallelizable tasks marked with [P] (when dependencies allow)
