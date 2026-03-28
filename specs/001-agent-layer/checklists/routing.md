# Multi-Agent Routing Checklist: Self-Managed Agent Layer

**Purpose**: Validate multi-agent routing requirements quality
**Created**: 2026-03-25
**Updated**: 2026-03-27
**Feature**: [link](../spec.md)

## Routing Completeness

- [x] CHK201 - Is the intent classification mechanism specified (keyword, LLM, rule-based)? ✅ Addressed - keyword-based
- [x] CHK202 - Are routing keywords for each agent type documented? ✅ Addressed - keyword table in spec
- [x] CHK203 - Is the default routing behavior when no intent matches specified? ✅ Addressed - fallback chain documented
- [x] CHK204 - Are agent capabilities and tool definitions complete? ✅ Addressed - Key Entities section

## Agent Coverage

- [x] CHK205 - Is QueryAgent tool set fully specified (weather, search, etc.)? ✅ Addressed - get_weather, web_search, get_time
- [x] CHK206 - Is BookingAgent tool set fully specified (search, book)? ✅ Addressed - search_hotels, book_hotel
- [x] CHK207 - Are flight booking tools specified or intentionally excluded? ✅ Addressed - excluded from v1
- [x] CHK208 - Is the mechanism for adding new agent types defined? ✅ Addressed - factory functions

## Routing Quality

- [x] CHK209 - Is routing accuracy measurable? ✅ Addressed - test scenarios defined
- [x] CHK210 - Are routing latency requirements specified? ✅ Addressed - same as SC-005 (300ms)
- [x] CHK211 - Is routing decision logging specified? ✅ Addressed - loguru with routing logs
- [x] CHK212 - Are ambiguous intent scenarios handled? ✅ Addressed - keyword count wins, ties → booking

## Conversation Continuity

- [x] CHK213 - Is conversation context maintained across agent handoffs? ✅ Addressed - TurnContext
- [x] CHK214 - Is conversation history format specified? ✅ Addressed - List[{role, content}]
- [x] CHK215 - Are multi-turn conversation requirements for routing defined? ✅ Addressed - 50 turn max
- [x] CHK216 - Is context isolation between agents specified? ✅ Addressed - shared TurnContext

## Integration Requirements

- [x] CHK217 - Is the agent factory/creation mechanism defined? ✅ Addressed - factory.py functions
- [x] CHK218 - Are concurrent agent instantiation requirements specified? ✅ Addressed - SC-003
- [x] CHK219 - Is agent lifecycle management defined? ✅ Addressed - ephemeral sessions
- [x] CHK220 - Are agent configuration requirements documented? ✅ Addressed - factory functions

## Testing & Validation

- [x] CHK221 - Are test scenarios for routing defined? ✅ Addressed - table in spec
- [x] CHK222 - Is the "independent test" criteria measurable? ✅ Addressed - User Story 3
- [x] CHK223 - Are edge cases (booking+query in same turn) addressed? ✅ Addressed - ambiguous intent section
- [x] CHK224 - Is the fallback to human handoff defined? ✅ Addressed - not in v1 scope

## Chrome MCP Considerations

- [ ] CHK225 - Are MCP tool definitions aligned with agent capabilities? ⚠️ Out of scope
- [ ] CHK226 - Is browser automation tool execution time considered in routing? ⚠️ Out of scope
- [ ] CHK227 - Are MCP-specific error handling requirements specified? ⚠️ Out of scope

## Updated 2026-03-27

All items except Chrome MCP addressed in spec.md. Chrome MCP marked as ⚠️ Out of scope for v1.
