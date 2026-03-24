# Tasks: Self-Managed Agent Layer

**Input**: Design documents from `/specs/001-agent-layer/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Project initialization and LangChain dependency

- [ ] T001 Create `src/server/agent/` directory structure
- [ ] T002 Add langchain, langchain-openai dependencies to requirements.txt
- [ ] T003 [P] Configure langchain logging for debugging

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create base agent interface in `src/server/agent/base.py`
- [ ] T005 Create StreamController in `src/server/agent/stream_controller.py`
- [ ] T006 Implement event emission system (tool_start, tool_progress, tool_complete, tool_error)
- [ ] T007 Integrate StreamController with existing `StreamingSynthesis` class
- [ ] T008 Create unit tests for StreamController in `tests/unit/agent/test_stream_controller.py`

**Checkpoint**: Foundational ready - agent layer can now be implemented

---

## Phase 3: User Story 1 - Non-Blocking Tool Calls (Priority: P1) 🎯 MVP

**Goal**: Tool calls do not block LLM stream

**Independent Test**: Trigger a tool call and verify TTS continues without >500ms silence

### Implementation for User Story 1

- [ ] T009 [P] [US1] Create LangChain agent wrapper in `src/server/agent/langchain_wrapper.py`
- [ ] T010 [US1] Integrate LangChain agent with StreamController for non-blocking events
- [ ] T011 [US1] Add tool event handlers that emit intermediate TTS text during execution
- [ ] T012 [US1] Modify `voice_turn.py` to use new agent layer instead of OpenAI LLM direct calls
- [ ] T013 [US1] End-to-end test: verify TTS continues during simulated tool call

**Checkpoint**: User Story 1 should be fully functional

---

## Phase 4: User Story 2 - Voice Booking Flow (Priority: P1)

**Goal**: User can book hotels via voice with continuous stream

**Independent Test**: Say "book a hotel for tomorrow" and verify booking flow completes

### Implementation for User Story 2

- [ ] T014 [P] [US2] Create booking tool definitions in `src/server/agent/tools/booking.py`
- [ ] T015 [US2] Create BookingAgent in `src/server/agent/booking_agent.py`
- [ ] T016 [US2] Implement hotel booking ReAct prompt template
- [ ] T017 [US2] Add booking confirmation TTS events
- [ ] T018 [US2] Integration test: booking flow with stream continuity

**Checkpoint**: Booking flow functional with non-blocking stream

---

## Phase 5: User Story 3 - Multi-Agent Routing (Priority: P2)

**Goal**: Different tasks routed to appropriate agents

**Independent Test**: Send booking vs query intent, verify correct agent handles each

### Implementation for User Story 3

- [ ] T019 [P] [US3] Create query tool definitions in `src/server/agent/tools/query.py`
- [ ] T020 [US3] Create QueryAgent in `src/server/agent/query_agent.py`
- [ ] T021 [US3] Implement AgentRouter in `src/server/agent/router.py` with intent classification
- [ ] T022 [US3] Add routing decision logging
- [ ] T023 [US3] Test routing for booking vs query intents

**Checkpoint**: Multi-agent routing functional

---

## Phase 6: User Story 4 - Interruption Handling (Priority: P1)

**Goal**: User can interrupt agent at any time

**Independent Test**: Speak during agent response, verify new input is processed

### Implementation for User Story 4

- [ ] T024 [P] [US4] Add interruption detection to TurnContext
- [ ] T025 [US4] Implement tool call cancellation in StreamController
- [ ] T026 [US4] Add TTS fallback text during interruption
- [ ] T027 [US4] Test interruption during tool execution

**Checkpoint**: Interruption handling functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T028 [P] Documentation: Update `docs/agent-layer.md` with architecture overview
- [ ] T029 Code cleanup and refactoring of agent module
- [ ] T030 Performance optimization: verify <200ms stream gap during tool calls
- [ ] T031 [P] Add integration tests in `tests/integration/test_agent_layer.py`
- [ ] T032 Security: audit tool definitions for safe execution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Non-blocking) → US2 (Booking) → US3 (Routing) → US4 (Interruption)
- **Polish (Final Phase)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 (uses same agent wrapper)
- **User Story 3 (P3)**: Depends on US1 (adds routing)
- **User Story 4 (P1)**: Depends on US1 (interruption during tool calls)

### Within Each User Story

- Base classes before concrete implementations
- Tests before implementation (if TDD requested)
- Story complete before moving to next priority

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Non-blocking Tool Calls)
4. **STOP and VALIDATE**: Test stream continuity during tool calls
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → Test stream continuity → Deploy/Demo
3. Add US2 → Test booking flow → Deploy/Demo
4. Add US3 → Test routing → Deploy/Demo
5. Add US4 → Test interruption → Deploy/Demo
6. Polish → Final release
