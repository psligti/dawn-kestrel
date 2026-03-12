---
id: SPEC-<repo>-<slug>           # REQUIRED: Globally unique ID, e.g., SPEC-dawn-kestrel-cli-surface
title: ""                         # REQUIRED: Human-readable title
repo: dawn-kestrel                # REQUIRED: dawn-kestrel|ash-hawk|neon-wren|bolt-merlin|iron-rook
owners: [suite-maintainers]       # REQUIRED: Default or customized owner list
status: draft                     # REQUIRED: draft|active|done|deprecated
horizon: near-future              # REQUIRED: shipped|near-future|moonshot
created: YYYY-MM-DD               # REQUIRED: Creation date
last_updated: YYYY-MM-DD          # REQUIRED: Last modification date
review_by: YYYY-MM-DD             # REQUIRED: Review deadline
related_docs:
  prds: []                        # Links to Product Requirements Documents
  adrs: []                        # Links to Architecture Decision Records
  roadmaps: []                    # Links to roadmap entries
  specs: []                       # Links to related specs
code_paths: []                    # Files/modules involved. Use "planned:" prefix for future work.
interfaces: []                    # Exposed interfaces, e.g., "cli:<cmd>", "api:<route>", "event:<name>"
success_signals: []               # Observable indicators that this spec is fulfilled
---

# [Title]

Brief one-line description of what this spec covers.

---

## intent

What this spec describes and why it matters.

- What problem does this solve?
- Who benefits from this work?
- Why is this the right approach?

---

## scope

What's in scope for this spec.

- Specific features, components, or behaviors covered
- Boundaries of the work
- What this spec explicitly addresses

---

## non-goals

Explicitly what this does NOT cover.

- Related work that's out of scope
- Problems this spec won't solve
- Future considerations deferred elsewhere

---

## current state

**For `horizon: shipped`:** Document what exists now. Reference actual code paths and interfaces.

**For `horizon: near-future` or `moonshot`:** Describe the baseline. What's the starting point?

- Current implementation status
- Existing code paths (with links)
- Known gaps or limitations

---

## target state

What we're building toward.

- Desired end state
- Key capabilities to deliver
- How success looks when complete

---

## design notes

Architecture decisions, patterns, and constraints.

- Key technical decisions
- Patterns to follow or avoid
- Integration points with other systems
- Performance or security considerations

---

## delivery plan

**For `horizon: near-future`:** Define phases and milestones with priorities.

**For `horizon: shipped`:** Document the history of how this was delivered.

**For `horizon: moonshot`:** Outline exploratory phases or proof-of-concept steps.

| Phase | Priority | Description | Dependencies |
|-------|----------|-------------|--------------|
| P0    | Must     | Core functionality | None |
| P1    | Should   | Enhancements | P0 |
| P2    | Nice     | Polish | P1 |

---

## validation

How to verify the spec is correct and complete.

- Test scenarios or acceptance criteria
- Review checkpoints
- Signals that indicate the spec needs updates

---

## risks & trade-offs

Known risks, open questions, and alternatives considered.

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ... | Low/Medium/High | Low/Medium/High | ... |

**Open Questions:**
1. Question that needs resolution before/during implementation

**Alternatives Considered:**
- Alternative A: Why not chosen
- Alternative B: Why not chosen

---

## references

Links to PRDs, ADRs, code, and other specs.

**IMPORTANT:** Link to existing documents rather than duplicating their content. Each reference should include a brief role statement explaining its relevance.

| Document | Location | Role |
|----------|----------|------|
| PRD-XXX | `docs/prds/xxx.md` | Defines product requirements |
| ADR-XXX | `docs/adrs/xxx.md` | Architecture decision context |
| Spec-XXX | `docs/specs/xxx.md` | Related technical specification |

---

## horizon-specific guidance

### shipped

Use this horizon for features that are complete and deployed.

- `code_paths` must reference actual, existing files
- `interfaces` must list real, working interfaces
- `current state` documents the shipped implementation
- Focus on evidence and verification

### near-future

Use this horizon for work planned in the next 1-2 quarters.

- Define clear priorities (P0/P1/P2)
- List dependencies and blockers
- Specify measurable `success_signals`
- `code_paths` may include `planned:` prefix for future work

### moonshot

Use this horizon for exploratory or long-term ideas.

- Focus on architectural fit and alignment
- Identify the biggest risk or uncertainty
- Require 2+ open questions per idea
- `code_paths` typically use `planned:` prefix
- `success_signals` may be speculative

---

## status lifecycle

| Status | Meaning | Next States |
|--------|---------|-------------|
| `draft` | Work in progress, not yet approved | `active` |
| `active` | Approved and being implemented | `done`, `deprecated` |
| `done` | Implementation complete | `deprecated` |
| `deprecated` | No longer relevant, superseded | (terminal) |

---

## template usage

1. Copy this template to `docs/specs/<slug>-spec.md`
2. Replace placeholder values in YAML frontmatter
3. Fill in each section with spec-specific content
4. Update `last_updated` on each modification
5. Link related documents in `related_docs` section
6. Keep `horizon` and `status` accurate as work progresses
