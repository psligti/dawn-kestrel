# Problems - review-harness-refactor

## Unresolved Blockers

(None currently)

## Questions / Ambiguities

None identified yet. Will update as work progresses.

## Risks

- **Risk 1**: Breaking changes to ReviewOutput schema could break downstream consumers
  - Mitigation: Strict schema validation, exhaustive parity tests
- **Risk 2**: Parent merge conflicts causing significant rework
  - Mitigation: Merge before and after each wave, resolve immediately
- **Risk 3**: LLM client abstraction introducing behavioral changes
  - Mitigation: Baseline tests before and after, careful validation
- **Risk 4**: FSM/budget logic altering existing review outputs
  - Mitigation: Test with disabled FSM initially, validate no changes

## Workarounds Applied

(None yet)

## Need Escalation

None yet
