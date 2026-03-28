# Data Model: Browser Booking Automation

**Branch**: `003-browser-booking-automation`
**Date**: 2026-03-28

## Entities

### BookingSession

Represents a complete hotel booking transaction.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | Yes | Unique identifier for this booking session |
| current_stage | int | Yes | Current stage index (0-6) |
| selected_hotel | HotelOption | No | User-selected hotel |
| selected_room | RoomOption | No | User-selected room |
| guest_info | GuestInfo | No | Guest name and email |
| checkin | string | No | Check-in date (YYYY-MM-DD) |
| checkout | string | No | Check-out date (YYYY-MM-DD) |
| guests | int | No | Number of guests |
| rooms | int | No | Number of rooms |
| created_at | datetime | Yes | Session creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

### HotelOption

Search result item from Booking.com.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique identifier (derived from URL) |
| name | string | Yes | Hotel name |
| price | string | No | Price in CNY format ("CNY 12,123") |
| score | string | No | Rating score ("8.8") |
| location | string | No | Area/neighborhood |
| url | string | Yes | Full Booking.com URL |

### RoomOption

Room type on hotel property page.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique identifier |
| name | string | Yes | Room type name |
| price | string | No | Price per night |
| max_guests | int | No | Maximum occupancy |
| bed_type | string | No | Bed configuration |

### GuestInfo

Guest contact information.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Guest full name |
| email | string | No | Email address |

### StageResult

Execution result from each stage tool.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| stage | string | Yes | Stage name (e.g., "search", "select_hotel") |
| action | StageAction | Yes | Next action enum |
| data | dict | No | Stage-specific payload |
| message | string | No | User-facing message |
| options | list[Option] | No | Selection options if WAIT_FOR_SELECTION |
| error | string | No | Error message if action is ERROR |

### StageAction (Enum)

| Value | Description | Next Behavior |
|-------|-------------|---------------|
| CONTINUE | Auto-proceed to next stage | System continues automatically |
| WAIT_FOR_SELECTION | User must select option | System presents options |
| WAIT_FOR_CONFIRMATION | User must confirm | System shows summary |
| COMPLETE | Booking finished | Payment page reached |
| ERROR | Stage failed | Report error, suggest retry |

### Option

Selection option presented to user.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| index | int | Yes | 1-based position in list |
| id | string | Yes | Option identifier |
| name | string | Yes | Short name |
| display | string | Yes | Full display string |
| details | dict | No | Additional data |

### TurnContext

Ephemeral state for current voice turn.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | Yes | Links to BookingSession |
| stage_index | int | Yes | Current stage (0-6) |
| booking_data | dict | Yes | Accumulated booking data |
| user_inputs | list[str] | No | User input history |
| errors | list[str] | No | Error messages |
| selected_items | dict | No | User selections by category |

## State Transitions

### Stage Flow

```
[search] → [select_hotel] → [navigate_property] → [select_room]
         → [confirm_selection] → [fill_guest] → [finalize]
```

### StageAction Transitions

| Current Action | Next Stage Trigger |
|---------------|-------------------|
| CONTINUE | Stage completed successfully |
| WAIT_FOR_SELECTION | Await user selection |
| WAIT_FOR_CONFIRMATION | Await user confirmation |
| COMPLETE | Finalize completed |
| ERROR | Stage failed after retries |

## Validation Rules

| Entity | Rule |
|--------|------|
| BookingSession.guests | Must be 1-10 |
| BookingSession.rooms | Must be 1-5 |
| HotelOption.url | Must start with "https://www.booking.com/hotel/" |
| GuestInfo.email | If provided, must be valid email format |
| StageResult.action | Must be valid StageAction enum value |
