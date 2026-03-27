# Multi-Agent Routing Checklist: Self-Managed Agent Layer

**Purpose**: Validate multi-agent routing requirements quality
**Created**: 2026-03-25
**Updated**: 2026-03-27
**Feature**: [link](../spec.md)

## Routing Completeness

- [ ] CHK201 - Is the intent classification mechanism specified (keyword, LLM, rule-based)? [Clarity] ❌ Phase 5
- [ ] CHK202 - Are routing keywords for each agent type documented? [Completeness] ❌ Phase 5
- [ ] CHK203 - Is the default routing behavior when no intent matches specified? [Edge Case] ❌ Phase 5
- [x] CHK204 - Are agent capabilities and tool definitions complete? [Completeness] ✅ data-model.md

## Agent Coverage

- [x] CHK205 - Is QueryAgent tool set fully specified (weather, search, etc.)? [Gap] ✅ data-model.md has get_weather, search_web, get_time
- [x] CHK206 - Is BookingAgent tool set fully specified (search, book)? [Gap] ✅ data-model.md has search_hotels, book_hotel, search_flights, book_flight
- [ ] CHK207 - Are flight booking tools specified or intentionally excluded? [Scope] ❌ flight tools defined but not implemented
- [ ] CHK208 - Is the mechanism for adding new agent types defined? [Gap] ❌ Phase 5

## Routing Quality

- [ ] CHK209 - Is routing accuracy measurable? [Measurability] ❌ Phase 5
- [ ] CHK210 - Are routing latency requirements specified? [Gap] ❌ Phase 5
- [ ] CHK211 - Is routing decision logging specified? [Completeness] ❌ Phase 5
- [ ] CHK212 - Are ambiguous intent scenarios handled? [Edge Case] ❌ Phase 5

## Conversation Continuity

- [x] CHK213 - Is conversation context maintained across agent handoffs? [Completeness] ✅ FR-006
- [ ] CHK214 - Is conversation history format specified? [Gap] ❌ format not defined
- [ ] CHK215 - Are multi-turn conversation requirements for routing defined? [Gap] ❌ Phase 5
- [ ] CHK216 - Is context isolation between agents specified? [Gap] ❌ Phase 5

## Integration Requirements

- [x] CHK218 - Are concurrent agent instantiation requirements specified? [Completeness] ✅ SC-003
- [ ] CHK219 - Is agent lifecycle management defined? [Gap] ❌ Phase 5
- [ ] CHK220 - Are agent configuration requirements documented? [Gap] ❌ Phase 5

## Testing & Validation

- [x] CHK221 - Are test scenarios for routing defined? [Completeness] ✅ User Story 3 acceptance scenarios
- [ ] CHK222 - Is the "independent test" criteria measurable? [Measurability] ❌ Phase 5
- [ ] CHK223 - Are edge cases (booking+query in same turn) addressed? [Edge Case] ❌ Phase 5
- [ ] CHK224 - Is the fallback to human handoff defined? [Gap] ❌ out of scope

## Chrome MCP Considerations

- [x] CHK225 - Are MCP tool definitions aligned with agent capabilities? [Alignment] ✅ Assumptions: Chrome MCP out-of-scope
- [x] CHK226 - Is browser automation tool execution time considered in routing? [Gap] ✅ Assumptions: out-of-scope
- [x] CHK227 - Are MCP-specific error handling requirements specified? [Gap] ✅ Assumptions: out-of-scope

## Notes

**Updated 2026-03-27**: routing 相关缺口主要是 Phase 5 的工作

Most routing items (CHK201-203, 208-215, 219-224) are deferred to Phase 5 implementation.

Items addressed this session:
- CHK204: Agent capabilities documented
- CHK205/206: Tool sets specified in data-model.md
- CHK213: Context maintenance (FR-006)
- CHK218: Concurrent instantiation (SC-003)
- CHK221: Test scenarios defined
- CHK225-227: Chrome MCP marked as out-of-scope

Remaining Phase 5 items:
- Intent classification mechanism
- Routing keywords and default behavior
- Multi-turn conversation requirements
- Agent lifecycle management
