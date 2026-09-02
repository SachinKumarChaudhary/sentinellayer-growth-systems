# Multi-Agent Operating Protocol

**Status:** Active engineering protocol  
**Authority:** Repository source of truth  
**Purpose:** Coordinate parallel subsystem sessions without requiring the product owner to relay implementation messages between sessions.

## 1. Communication model

Chat sessions cannot directly message one another. Therefore cross-session communication MUST occur through repository artifacts:

- GitHub branches and commits — implementation state
- Pull requests — proposed changes and review context
- Issues — blockers, dependency requests, and cross-system coordination
- `docs/handoffs/` — durable subsystem status and next actions
- `schemas/` — authoritative machine-readable interfaces
- CI — automated compatibility and quality signals

The product owner is not required to manually relay technical information between agents.

## 2. Platform coordination role

Platform is the coordination authority for shared interfaces, not the manager of domain implementation.

Platform owns:
- shared contracts and schemas
- canonical cross-system identifiers
- event envelope conventions
- contract compatibility
- cross-system integration tests
- shared validation primitives
- coordination of interface changes

Platform does not own other systems' business logic.

## 3. Agent startup protocol

Every subsystem session MUST:

1. Fetch the latest repository state.
2. Read the master system contracts.
3. Read ownership and dependency documentation.
4. Read its subsystem specification.
5. Inspect recent commits and open relevant PRs/issues.
6. Inspect relevant schemas and migrations.
7. Determine its current milestone and dependencies.
8. Only then implement.

Conversation memory is supplementary. Repository state is authoritative.

## 4. Parallel development protocol

Each subsystem should work from an isolated branch or PR.

Before modifying a file:
- verify the file is within the subsystem's ownership;
- fetch its current contents;
- check recent changes;
- avoid overwriting concurrent work.

Do not force-push or rewrite shared history.

If two sessions need the same file, coordinate through a PR/issue or have Platform define the required boundary. Do not resolve the conflict by silently taking ownership.

## 5. Contract-change protocol

When a producer or consumer needs a shared interface change:

```
Requirement
  -> identify producer + consumers
  -> Platform compatibility review
  -> backward-compatible change OR versioned breaking change
  -> producer/consumer implementation
  -> integration test
  -> CI
```

A subsystem MUST NOT silently change a shared contract merely to make its local implementation pass.

## 6. Handoff protocol

Each active subsystem maintains:

`docs/handoffs/<subsystem>.md`

A handoff records:

- current status
- completed work
- current branch / PR
- exact files changed
- database/migration changes
- contract/schema changes
- tests and results
- dependencies
- blockers
- known risks
- next action
- receiving subsystem where applicable

Handoffs are append/update points for durable coordination, not a replacement for authoritative code or schemas.

## 7. Issue/PR protocol

Use an Issue when:
- another subsystem is blocked;
- a contract decision is needed;
- ownership is ambiguous;
- a dependency is missing.

Use a PR when:
- implementation is ready for review;
- a shared contract is being changed;
- integration behavior needs review.

Cross-system PRs should explicitly state:
- producer
- consumer
- contract
- compatibility impact
- tests proving the boundary

## 8. No direct cross-session assumptions

Agents MUST NOT assume:
- another session has seen a chat message;
- another session has read a new implementation;
- a branch is current;
- a contract exists merely because it was discussed.

They MUST verify repository state.

## 9. Completion gate

A subsystem milestone is complete only when applicable:

- implementation is tested;
- contract validation passes;
- integration tests pass;
- database/RLS requirements pass;
- CI passes;
- documentation/handoff is updated;
- ownership boundaries remain intact.

If blocked by another subsystem, report `BLOCKED` rather than implementing an unauthorized workaround.

## 10. Product-owner escalation

Escalate to the product owner only for decisions that require product/strategy authority, such as:
- business strategy;
- offer/pricing decisions;
- target behavior not specified by contracts;
- acceptance criteria that are genuinely undefined.

Technical coordination should normally be resolved through the repository and Platform contract process.
