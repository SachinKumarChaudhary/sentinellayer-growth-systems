# Platform Contract Validation Plan

**Status:** Active  
**Owner:** Platform

## Objective

Turn the existing system contracts into executable compatibility gates while allowing Campaign, Mail, Tracking, and Conversation to evolve independently.

Intelligence and Sales are future systems at this stage. Their interfaces may be specified and contract-tested with fixtures, but Platform must not implement their domain logic or create speculative runtime components.

## Current integration boundaries

### Implemented/active boundary targets

```
Campaign
  -> RenderedSendTreatment
  -> Mail
  -> ProviderOutcome
  -> Tracking
  -> Conversation
```

### Future boundary targets

```
Intelligence
  -> IntentSnapshot
  -> Campaign

Conversation
  -> ConversationHandoff
  -> Sales

Sales
  -> SalesHandoff
  -> Analytics
```

Future boundaries should use contract fixtures until the owning runtime exists.

## Validation layers

1. **Schema validation**
   - every payload validates against its declared schema/version
   - required identifiers are present
   - enums and lifecycle states are constrained

2. **Identity preservation**
   - canonical IDs are not silently regenerated between systems
   - correlation IDs survive the complete event chain
   - historical version identifiers remain attributable

3. **Boundary validation**
   - producer output is accepted by the declared consumer
   - invalid producer output is rejected
   - unknown/unsupported contract versions fail explicitly

4. **State ownership**
   - a consumer cannot silently mutate producer-owned state
   - cross-system transitions occur through the defined contract/interface

5. **Idempotency**
   - repeated delivery of the same event/request does not create duplicate durable effects

6. **Failure handling**
   - ambiguous outcomes remain ambiguous
   - suppression/safety failures fail closed
   - downstream unavailability does not corrupt upstream durable state

7. **Traceability**
   - account/person/campaign/enrollment/send/conversation identifiers remain attributable
   - provider and behavioral events retain their correlation context

## Synthetic lifecycle test

The eventual end-to-end test should use synthetic records only:

```
synthetic account
  -> synthetic person
  -> synthetic campaign enrollment
  -> rendered treatment
  -> send request
  -> mock provider outcome
  -> synthetic tracking event
  -> synthetic conversation/reply
  -> future sales handoff fixture
  -> attribution fixture
```

No real prospect, domain, mailbox, or provider should be required for this gate.

## Parallel-agent rule

Platform tests must consume public contracts rather than importing another subsystem's private implementation details.

This allows subsystem agents to work in parallel without creating hidden coupling.

## Definition of done

- [ ] schemas validate
- [ ] producer/consumer compatibility is tested
- [ ] canonical identifiers are preserved
- [ ] versioning is tested
- [ ] idempotency is tested
- [ ] failure paths are tested
- [ ] current implemented boundaries have integration coverage
- [ ] future Intelligence/Sales boundaries have fixture-level contract coverage
- [ ] CI executes the contract gate
- [ ] no real outbound infrastructure is required
