# Multi-Agent Routing Checklist: Self-Managed Agent Layer

**Purpose**: Validate multi-agent routing requirements quality
**Created**: 2026-03-25
**Feature**: [link](../spec.md)

## Routing Completeness

- [ ] CHK201 - Is the intent classification mechanism specified (keyword, LLM, rule-based)? [Clarity, Spec §FR-005]
- [ ] CHK202 - Are routing keywords for each agent type documented? [Completeness, Gap]
- [ ] CHK203 - Is the default routing behavior when no intent matches specified? [Edge Case, Gap]
- [ ] CHK204 - Are agent capabilities and tool definitions complete? [Completeness, Spec §Key Entities]

## Agent Coverage

- [ ] CHK205 - Is QueryAgent tool set fully specified (weather, search, etc.)? [Gap, Spec §Key Entities]
- [ ] CHK206 - Is BookingAgent tool set fully specified (search, book)? [Gap, Spec §Key Entities]
- [ ] CHK207 - Are flight booking tools specified or intentionally excluded? [Scope, Gap]
- [ ] CHK208 - Is the mechanism for adding new agent types defined? [Gap]

## Routing Quality

- [ ] CHK209 - Is routing accuracy measurable? [Measurability, Spec §Success Criteria]
- [ ] CHK210 - Are routing latency requirements specified? [Gap]
- [ ] CHK211 - Is routing decision logging specified? [Completeness, Spec §FR-005]
- [ ] CHK212 - Are ambiguous intent scenarios handled? [Edge Case, Gap]

## Conversation Continuity

- [ ] CHK213 - Is conversation context maintained across agent handoffs? [Completeness, Spec §FR-006]
- [ ] CHK214 - Is conversation history format specified? [Gap]
- [ ] CHK215 - Are multi-turn conversation requirements for routing defined? [Gap]
- [ ] CHK216 - Is context isolation between agents specified? [Gap]

## Integration Requirements

- [ ] CHK217 - Is the agent factory/creation mechanism defined? [Completeness, Gap]
- [ ] CHK218 - Are concurrent agent instantiation requirements specified? [Completeness, Spec §SC-003]
- [ ] CHK219 - Is agent lifecycle management defined? [Gap]
- [ ] CHK220 - Are agent configuration requirements documented? [Gap]

## Testing & Validation

- [ ] CHK221 - Are test scenarios for routing defined? [Completeness, Spec §User Story 3]
- [ ] CHK222 - Is the "independent test" criteria measurable? [Measurability, Spec §User Story 3]
- [ ] CHK223 - Are edge cases (booking+query in same turn) addressed? [Edge Case, Gap]
- [ ] CHK224 - Is the fallback to human handoff defined? [Gap]

## Chrome MCP Considerations

- [ ] CHK225 - Are MCP tool definitions aligned with agent capabilities? [Alignment, Gap]
- [ ] CHK226 - Is browser automation tool execution time considered in routing? [Gap]
- [ ] CHK227 - Are MCP-specific error handling requirements specified? [Gap]

## Notes

- Intent classification is underspecified - recommend keyword-based MVP with LLM fallback
- Flight booking tools missing from current scope
- Chrome MCP integration not reflected in requirements
