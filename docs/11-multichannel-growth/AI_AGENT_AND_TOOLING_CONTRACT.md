# Sentinel Layer — AI Agent, Tooling and Integration Contract

**Status:** Canonical design baseline  
**Date:** 2026-09-08

## 1. Purpose

Prevent later agents from confusing research, execution, system-of-record responsibilities, or inventing tool capabilities.

## 2. Sentinel Layer

Sentinel Layer owns:

- Companies
- Decision makers
- Company contacts
- Intent signals
- Campaigns
- Campaign batches
- Enrollments
- Touchpoints
- Conversations
- Tracking events
- Recommendations
- Meetings
- Attribution
- Suppression/safety state

Sentinel Layer is the durable source of truth.

## 3. TinyFish

Use TinyFish Search + Fetch for public web research/enrichment.

Use it within the actual rate limits.

Do not assume TinyFish is the bulk execution system.

Use caching and avoid repeated fetches.

## 4. AI research agents

ChatGPT/Gemini-class agents may perform research tasks over public information and return structured evidence.

Research tasks:

- Company enrichment
- Decision-maker discovery
- Public email/phone/social discovery
- Buying-intent detection
- Public source verification

An AI agent must return evidence, not unsupported assertions.

## 5. Apify

Apify is used for **email finding/enrichment** in this architecture.

Do not assign general-purpose website scraping responsibility to Apify unless a future design decision explicitly changes this contract.

## 6. QEV / Email Hippo

Use as email verification stages after free evidence/oracle filtering.

Paid verification should be minimized through candidate ranking and free prechecks.

## 7. Composio

Composio is the integration/execution layer for supported social platforms:

- LinkedIn
- Instagram
- Reddit

Architecture:

```
Sentinel Layer
  -> Channel Adapter
  -> Composio
  -> Connected platform
```

Composio may be accessed via SDK/API and via agent/MCP tooling.

The implementation must validate actual connected account capabilities and required scopes before relying on a specific action.

Do not invent an action because a toolkit exists.

## 8. Hermes

Hermes is the operating agent.

It may:

- run research
- use MCP/tooling
- use Composio
- inspect recommendations
- prepare or execute operator-approved actions
- assist with campaign operations

Hermes does not replace Sentinel Layer as the system of record.

## 9. Operator

The human/operator controls revenue-sensitive actions.

Expected loop:

```
AI research
 -> AI recommendation
 -> AI draft
 -> operator approval
 -> execution
 -> event capture
 -> updated recommendation
```

## 10. AI scoring boundary

When a deterministic rule exists in the approved playbook, AI should not invent an alternative scoring logic.

Examples:

- FIT scoring
- INTENT decay
- suppression/caps
- role ranking rules

AI may summarize and explain the evidence.

## 11. AI recommendation boundary

AI may recommend:

- target person
- reason to contact now
- channel sequence
- personalization angle
- follow-up
- social warming
- message draft
- content topic

Recommendations must preserve supporting evidence.

## 12. No hallucinated integrations

Before implementing a platform-specific action:

1. Inspect the available Composio/tool capability.
2. Confirm authentication/scopes.
3. Confirm the action actually exists.
4. Confirm the action is appropriate for the connected account.
5. Implement behind a channel adapter.

## 13. Failure behavior

If automation is unavailable:

```
action unavailable
 -> operator task
 -> human executes
 -> outcome recorded
```

Do not silently drop the interaction from the system.

## 14. Auditability

Every AI-produced recommendation that leads to execution should retain:

- recommendation ID
- source signals
- generated_at
- model/agent source where appropriate
- approval identity
- approval timestamp
- resulting touchpoint/event

This makes recommendations auditable.
