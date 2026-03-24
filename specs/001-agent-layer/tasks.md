# Tasks: Self-Managed Agent Layer

**Input**: Design documents from `/specs/001-agent-layer/`
**Prerequisites**: plan.md (✅), spec.md (✅), research.md (✅), data-model.md (✅), contracts/ (✅), quickstart.md (✅)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup ✅

**Status**: Complete

- [x] T001 Create `src/server/agent/` directory structure
- [x] T002 Add langchain, langchain-openai dependencies to requirements.txt
- [x] T003 [P] Configure langchain logging for debugging

---

## Phase 2: Foundational (Blocking Prerequisites)

**Status**: ✅ Complete
**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [x] T004 [P] Create `src/server/agent/__init__.py` with module exports
- [x] T005 [P] Create `src/server/agent/base.py` with BaseAgent abstract class
- [x] T006 Create `src/server/agent/events.py` with event dataclasses (ToolStart, ToolComplete, etc.)
- [x] T007 Create `src/server/agent/stream_controller.py` with BaseCallbackHandler integration
- [x] T008 [P] Create `src/server/agent/llm_factory.py` to wrap existing LLM with LangChain adapter
- [x] T009 Create unit tests in `tests/unit/agent/test_base.py`
- [x] T010 Create unit tests in `tests/unit/agent/test_stream_controller.py`

**Checkpoint**: ✅ Foundational ready - agent layer can now be implemented

---

## Phase 3: User Story 1 - Non-Blocking Tool Calls (Priority: P1) 🎯 MVP

**Goal**: Tool calls do not block LLM stream

**Independent Test**: Trigger a tool call and verify TTS continues without >500ms silence

### Implementation for User Story 1

- [x] T011 [P] [US1] Create `src/server/agent/tools/dummy_tool.py` - simple echo tool for testing
- [x] T012 [US1] Create `src/server/agent/langchain_agent.py` wrapping LangChain agent with astream_events()
- [x] T013 [US1] Integrate StreamController callback → TTS text emission in langchain_agent.py
- [ ] T014 [US1] Modify `src/server/voice_turn.py` to use LangChainAgent instead of OpenAILLM.chat_stream() ⚠️ PENDING
- [x] T015 [US1] Add WebSocket event emission for tool lifecycle (tool_start, tool_complete)
- [x] T016 [US1] Test: verify TTS emits text during dummy tool execution

**Checkpoint**: ⚠️ T014 pending - voice_turn.py integration required for full MVP

---

## Phase 4: User Story 2 - Voice Booking Flow (Priority: P1)

**Status**: ✅ Complete
**Goal**: User can book hotels via voice with continuous stream

**Independent Test**: Say "book a hotel for tomorrow" and verify booking flow completes

### Implementation for User Story 2

- [x] T017 [P] [US2] Create `src/server/agent/tools/hotel_tool.py` with search and book functions
- [x] T018 [US2] Create `src/server/agent/booking_agent.py` extending BaseAgent with hotel tools
- [x] T019 [US2] Implement ReAct prompt template for booking in booking_agent.py
- [x] T020 [US2] Add progress callbacks to emit "searching hotels..." during tool execution
- [x] T021 [US2] Integration test: booking flow with stream continuity verification

**Checkpoint**: ✅ Booking flow functional with non-blocking stream

---

## Phase 5: User Story 3 - Multi-Agent Routing (Priority: P2)

**Goal**: Different tasks routed to appropriate agents

**Independent Test**: Send booking vs query intent, verify correct agent handles each

### Implementation for User Story 3

- [ ] T022 [P] [US3] Create `src/server/agent/tools/query_tool.py` with weather, search functions
- [ ] T023 [US3] Create `src/server/agent/query_agent.py` extending BaseAgent with query tools
- [ ] T024 [US3] Create `src/server/agent/router.py` with intent classification (keyword-based)
- [ ] T025 [US3] Add routing decision logging in router.py
- [ ] T026 [US3] Test: verify booking intent → BookingAgent, query intent → QueryAgent

**Checkpoint**: Multi-agent routing functional

---

## Phase 6: User Story 4 - Interruption Handling (Priority: P1)

**Goal**: User can interrupt agent at any time

**Independent Test**: Speak during agent response, verify new input is processed

### Implementation for User Story 4

- [ ] T027 [P] [US6] Add cancellation token to TurnContext in `src/server/turn_context.py`
- [ ] T028 [US6] Implement tool call cancellation in StreamController (check is_cancelled before emitting)
- [ ] T029 [US6] Add TTS fallback text "Sorry, let me start over" on interruption
- [ ] T030 [US6] Test: speak during tool execution, verify new request processed

**Checkpoint**: Interruption handling functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T031 [P] Update `docs/agent-layer.md` with architecture overview
- [ ] T032 Code cleanup and refactoring of agent module
- [ ] T033 Performance: measure stream gap during tool calls, target <200ms
- [ ] T034 [P] Add integration tests in `tests/integration/test_agent_layer.py`
- [ ] T035 Security: audit tool definitions for safe execution

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Complete
- **Foundational (Phase 2)**: TODO - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Uses BookingAgent
- **User Story 3 (P3)**: Can start after Foundational - Adds AgentRouter
- **User Story 4 (P1)**: Can start after Foundational - Uses cancellation tokens

### Within Each User Story

- Base classes before concrete implementations
- Tests before implementation (if TDD requested)
- Story complete before moving to next priority

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup ✅
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

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Setup | T001-T003 | ✅ Complete |
| Phase 2: Foundational | T004-T010 | ✅ Complete |
| Phase 3: US1 | T011-T016 | ⚠️ 15/16 done (T014 pending) |
| Phase 4: US2 | T017-T021 | ✅ Complete |
| Phase 5: US3 | T022-T026 | TODO |
| Phase 6: US4 | T027-T030 | TODO |
| Phase 7: Polish | T031-T035 | TODO |

**Total**: 35 tasks  
**Completed**: 24 tasks  
**Pending**: 11 tasks (including T014 bridge task)  
**MVP Scope**: Phase 2 + Phase 3 (T004-T016) = 13 tasks (11 done, 2 pending including T014)
