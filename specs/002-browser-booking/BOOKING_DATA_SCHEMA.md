# BookingData Schema

**Status**: Design Complete
**Version**: 1.0

---

## Overview

`BookingData` is the state container accumulated across the 7-stage hotel booking flow:

```
SEARCH → RESULTS → PROPERTY → ROOM → SELECTION → GUEST → PAYMENT
```

Design principles:
1. **Append-only history** - changes create new `SelectionRecord` entries, never destroy
2. **Forward-clearing** - changing a parent selection auto-clears children
3. **Nullable fields** - partial info is valid until stage transition validation
4. **Immutable snapshots** - `Hotel`, `Room` objects are frozen once stored

---

## Complete Schema

```python
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class BookingStage(Enum):
    """7-stage booking flow progression."""
    SEARCH = "search"
    RESULTS = "results"
    PROPERTY = "property"
    ROOM = "room"
    SELECTION = "selection"
    GUEST = "guest"
    PAYMENT = "payment"


class SelectionStrategy(Enum):
    """How user selected an item (for audit/history)."""
    VOICE_INDEX = "voice_index"    # "pick #1"
    VOICE_NAME = "voice_name"      # "Hotel A"
    VOICE_PREFERENCE = "voice_preference"  # "cheapest", "closest"
    MANUAL = "manual"


@dataclass
class GuestProfile:
    """Pre-booking user info collected early or from user profile."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None          # International format
    nationality: Optional[str] = None    # ISO 3166-1 alpha-2

    def is_complete(self) -> bool:
        return all([self.name, self.email, self.phone])

    def missing_fields(self) -> List[str]:
        return [f for f in ["name", "email", "phone"] if getattr(self, f) is None]


@dataclass
class SearchParams:
    """Stage 1: Search parameters."""
    destination: str
    checkin: date
    checkout: date
    rooms: int = 1
    adults: int = 2
    children: int = 0

    # Optional filters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    star_rating: Optional[List[int]] = None
    property_type: Optional[List[str]] = None
    user_preferences: Optional[str] = None

    def duration_nights(self) -> int:
        return (self.checkout - self.checkin).days

    def validate(self) -> List[str]:
        errors = []
        if self.checkout <= self.checkin:
            errors.append("checkout must be after checkin")
        if self.duration_nights() > 30:
            errors.append("stay cannot exceed 30 nights")
        if self.rooms > 5:
            errors.append("maximum 5 rooms per booking")
        return errors


@dataclass
class Hotel:
    """Hotel from search results (immutable once stored)."""
    id: str
    name: str
    location: str
    address: Optional[str] = None
    star_rating: Optional[float] = None
    review_score: Optional[float] = None
    review_count: Optional[int] = None
    review_category: Optional[str] = None
    price_per_night: float
    currency: str = "USD"
    thumbnail_url: Optional[str] = None
    amenities: List[str] = field(default_factory=list)
    raw_data: Optional[dict] = None


@dataclass
class SearchResults:
    """Stage 2: Cached search results."""
    search_id: str
    params: SearchParams
    hotels: List[Hotel] = field(default_factory=list)
    total_count: int = 0
    cached_at: datetime = field(default_factory=datetime.utcnow)
    page: int = 1
    page_size: int = 20

    def hotel_by_id(self, hotel_id: str) -> Optional[Hotel]:
        return next((h for h in self.hotels if h.id == hotel_id), None)


@dataclass
class Room:
    """Room type within a hotel."""
    id: str
    name: str
    description: Optional[str] = None
    price_per_night: float
    currency: str = "USD"
    max_occupancy: int = 2
    available_count: int = 0
    bed_type: Optional[str] = None
    bed_count: Optional[int] = None
    free_cancellation: bool = False
    pay_at_property: bool = False
    amenities: List[str] = field(default_factory=list)
    photo_url: Optional[str] = None
    raw_data: Optional[dict] = None


@dataclass
class RoomResults:
    """Stage 4: Cached room options for selected hotel."""
    hotel_id: str
    rooms: List[Room] = field(default_factory=list)
    cached_at: datetime = field(default_factory=datetime.utcnow)

    def room_by_id(self, room_id: str) -> Optional[Room]:
        return next((r for r in self.rooms if r.id == room_id), None)


@dataclass
class SelectionRecord:
    """Audit trail: how/why a selection was made."""
    strategy: SelectionStrategy
    raw_input: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_invocation_id: Optional[str] = None


@dataclass
class HotelSelection:
    """Stage 3: User's hotel selection."""
    hotel: Hotel
    selected_at: datetime = field(default_factory=datetime.utcnow)
    selection: SelectionRecord = field(default_factory=datetime.utcnow)
    search_id: Optional[str] = None
    previous_hotel_id: Optional[str] = None


@dataclass
class RoomSelection:
    """Stage 5: User's room selection."""
    room: Room
    hotel_id: str
    nights: int
    total_price: float
    currency: str = "USD"
    selected_at: datetime = field(default_factory=datetime.utcnow)
    selection: SelectionRecord = field(default_factory=datetime.utcnow)
    previous_room_id: Optional[str] = None


@dataclass
class BookingSummary:
    """Stage 6-7: Final booking data for confirmation."""
    hotel: Hotel
    room: Room
    search_params: SearchParams
    guest_info: GuestProfile
    nights: int
    room_total: float
    taxes_and_fees: float = 0.0
    total_price: float
    currency: str = "USD"
    confirmed_at: Optional[datetime] = None
    confirmation_number: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BookingData:
    """
    Complete booking context - accumulated across 7-stage flow.
    """
    # User profile (may be pre-filled)
    user_profile: GuestProfile = field(default_factory=GuestProfile)

    # Stage 1: Search
    search_params: Optional[SearchParams] = None
    search_results: Optional[SearchResults] = None

    # Stage 2-3: Hotel Selection
    hotel_selection: Optional[HotelSelection] = None

    # Stage 4: Room Selection
    room_results: Optional[RoomResults] = None
    room_selection: Optional[RoomSelection] = None

    # Stage 5-6: Guest Info & Summary
    guest_info: Optional[GuestProfile] = None
    booking_summary: Optional[BookingSummary] = None

    # State tracking
    current_stage: BookingStage = BookingStage.SEARCH
    selection_history: List[SelectionRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    def is_complete(self) -> bool:
        return (
            self.booking_summary is not None
            and self.booking_summary.guest_info.is_complete()
        )

    def progress_percentage(self) -> int:
        stages = [
            self.search_params is not None,
            self.search_results is not None,
            self.hotel_selection is not None,
            self.room_results is not None,
            self.room_selection is not None,
            self.guest_info is not None,
            self.booking_summary is not None,
        ]
        return int(sum(stages) / len(stages) * 100)

    def change_hotel(self, new_hotel: Hotel, selection: SelectionRecord) -> None:
        """Handle user changing hotel mid-way. Auto-clears downstream state."""
        if self.hotel_selection:
            self.selection_history.append(self.hotel_selection.selection)

        self.hotel_selection = HotelSelection(
            hotel=new_hotel,
            selection=selection,
            previous_hotel_id=self.hotel_selection.hotel.id if self.hotel_selection else None
        )
        self.room_results = None
        self.room_selection = None
        self.booking_summary = None
        self._update_timestamp()

    def change_room(self, new_room: Room, selection: SelectionRecord) -> None:
        """Handle user changing room selection."""
        if self.room_selection:
            self.selection_history.append(self.room_selection.selection)

        self.room_selection = RoomSelection(
            room=new_room,
            hotel_id=self.hotel_selection.hotel.id if self.hotel_selection else "",
            nights=self.search_params.duration_nights() if self.search_params else 1,
            total_price=new_room.price_per_night * (self.search_params.duration_nights() if self.search_params else 1),
            selection=selection,
            previous_room_id=self.room_selection.room.id if self.room_selection else None
        )
        self.booking_summary = None
        self._update_timestamp()

    def build_summary(self) -> BookingSummary:
        """Compute final booking summary from all stages."""
        if not all([self.hotel_selection, self.room_selection, self.guest_info, self.search_params]):
            raise ValueError("Cannot build summary: missing required data")

        nights = self.search_params.duration_nights()
        room_total = self.room_selection.room.price_per_night * nights

        self.booking_summary = BookingSummary(
            hotel=self.hotel_selection.hotel,
            room=self.room_selection.room,
            search_params=self.search_params,
            guest_info=self.guest_info,
            nights=nights,
            room_total=room_total,
            total_price=room_total,
        )
        return self.booking_summary

    def _update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()
```

---

## Answers to Design Questions

### 1. What is the complete schema?
See above. Nested dataclasses with clear stage mapping:
- `search_params` + `search_results` (Stage 1-2)
- `hotel_selection` (Stage 3)
- `room_results` + `room_selection` (Stage 4-5)
- `guest_info` + `booking_summary` (Stage 6-7)

### 2. How to handle partial/early info?
All fields are `Optional`/`None` by default. Each class has:
- `is_complete()` - checks if minimum viable data exists
- `missing_fields()` - returns list of required-but-missing fields

Validation happens at **stage transitions** (not on every update).

### 3. Immutable or updatable?
**Mutable with append-only history**:
- `selection_history: List[SelectionRecord]` tracks all changes
- `previous_hotel_id` / `previous_room_id` maintain chain
- Immutable: `Hotel`, `Room`, `SearchParams` objects never change after creation

### 4. How to handle conflicts (user changes hotel)?
```python
def change_hotel(self, new_hotel: Hotel, selection: SelectionRecord):
    # 1. Archive old selection
    self.selection_history.append(self.hotel_selection.selection)

    # 2. Replace with new
    self.hotel_selection = HotelSelection(hotel=new_hotel, ...)

    # 3. Auto-clear downstream state
    self.room_results = None      # Must re-fetch rooms
    self.room_selection = None     # Must re-select room
    self.booking_summary = None   # Must rebuild
```

---

## JSON Schema Equivalent

```json
{
  "$defs": {
    "GuestProfile": {
      "type": "object",
      "properties": {
        "name": {"type": ["string", "null"]},
        "email": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
        "nationality": {"type": ["string", "null"]}
      }
    },
    "SearchParams": {
      "type": "object",
      "required": ["destination", "checkin", "checkout"],
      "properties": {
        "destination": {"type": "string"},
        "checkin": {"type": "string", "format": "date"},
        "checkout": {"type": "string", "format": "date"},
        "rooms": {"type": "integer", "default": 1},
        "adults": {"type": "integer", "default": 2},
        "children": {"type": "integer", "default": 0},
        "min_price": {"type": ["number", "null"]},
        "max_price": {"type": ["number", "null"]}
      }
    },
    "Hotel": {
      "type": "object",
      "required": ["id", "name", "location", "price_per_night"],
      "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "location": {"type": "string"},
        "star_rating": {"type": ["number", "null"]},
        "review_score": {"type": ["number", "null"]},
        "price_per_night": {"type": "number"},
        "currency": {"type": "string", "default": "USD"}
      }
    },
    "Room": {
      "type": "object",
      "required": ["id", "name", "price_per_night"],
      "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "price_per_night": {"type": "number"},
        "max_occupancy": {"type": "integer"},
        "free_cancellation": {"type": "boolean"},
        "pay_at_property": {"type": "boolean"}
      }
    }
  },
  "type": "object",
  "properties": {
    "user_profile": {"$ref": "#/$defs/GuestProfile"},
    "search_params": {"$ref": "#/$defs/SearchParams"},
    "search_results": {
      "type": "object",
      "properties": {
        "search_id": {"type": "string"},
        "hotels": {"type": "array", "items": {"$ref": "#/$defs/Hotel"}}
      }
    },
    "hotel_selection": {
      "type": "object",
      "properties": {
        "hotel": {"$ref": "#/$defs/Hotel"},
        "previous_hotel_id": {"type": ["string", "null"]}
      }
    },
    "room_selection": {
      "type": "object",
      "properties": {
        "room": {"$ref": "#/$defs/Room"},
        "nights": {"type": "integer"},
        "total_price": {"type": "number"}
      }
    },
    "guest_info": {"$ref": "#/$defs/GuestProfile"},
    "booking_summary": {"type": ["object", "null"]}
  }
}
```

---

## Usage Examples

### Pre-fill user info early
```python
booking.user_profile = GuestProfile(
    name="张三",
    email="zhang@example.com",
    phone="+86-138-0000-0000"
)
```

### Search and select hotel
```python
booking.search_params = SearchParams(
    destination="东京",
    checkin=date(2026, 4, 1),
    checkout=date(2026, 4, 5),
    adults=2
)
booking.search_results = search_results
booking.hotel_selection = HotelSelection(
    hotel=results.hotel_by_id("h123"),
    selection=SelectionRecord(strategy=SelectionStrategy.VOICE_INDEX, raw_input="pick #1")
)
```

### Change hotel mid-way (conflict handling)
```python
booking.change_hotel(
    new_hotel=results.hotel_by_name("Hotel B"),
    selection=SelectionRecord(strategy=SelectionStrategy.VOICE_NAME, raw_input="Hotel B")
)
# room_results, room_selection, booking_summary are now None
```

### Complete and build summary
```python
booking.guest_info = booking.user_profile  # May have been pre-filled
booking.build_summary()
# booking.booking_summary now contains final confirmation data
```