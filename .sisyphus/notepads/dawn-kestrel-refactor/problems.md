# Problems

## Plugin Discovery Implementation (2026-02-08)

### None encountered
- No problems encountered during implementation


## Security Reviewer Test Failure (2026-02-09)

### Issue
Test: tests/review/agents/test_security_reviewer.py::TestSecurityReviewerLLMBased::test_review_includes_system_prompt_and_context_in_message
Error: captured_message is None (expected not None)

### Status
- Test exists in HEAD (pre-existing, not from refactor)
- Not part of dawn-kestrel-refactor plan tasks
- Likely pre-existing issue with test setup or mock configuration
- 535 other tests pass successfully

### Notes
- Test mocks AISession.process_message but captured_message remains None
- May be related to how the mock is set up or how reviewer.review() works
- Investigating this test is not in scope for current refactor plan
- Should be addressed separately if needed for production use

### Next Steps
- Document and ignore for now
- Focus on completing 46 tasks in dawn-kestrel-refactor plan

