# Sentinel Layer — Canonical Multi-Channel Growth System Design

**Status:** Canonical design baseline  
**Date:** 2026-09-08  
**Purpose:** Prevent architectural drift and hallucinated assumptions.

## 1. Objective

Build a company-centric growth system that helps a human operator generate more qualified meetings through coordinated email, LinkedIn, Instagram, Reddit, social content, first-party CTA tracking, conversations, and future phone workflows.

The objective is **not** channel-vs-channel optimization. Channels cooperate to create meetings and sales.

Primary KPI for the current phase: **meetings booked**.

## 2. System-of-record hierarchy

The canonical entities are:

```
Company
  -> Decision Makers
  -> Company Contacts
  -> Intent Signals
  -> Campaigns / Batches
  -> Touchpoints
  -> Conversations
  -> Tracking Events
  -> Recommendations
  -> Meetings
```

### Company

The company is the ICP-level object and the root of campaign planning.

### Decision Makers

Decision makers are the actionable people associated with a company. Their contact surfaces live inside the decision-maker record.

A company may have multiple decision makers and multiple campaigns may target different decision makers.

### Company Contacts

Generic organization-level contact routes such as info@, hello@, support@, sales@, press@, main phone, etc. are separate from decision makers.

### Touchpoint

A concrete outreach or interaction attempt on a channel. A touchpoint may be email, LinkedIn DM, social interaction, Reddit DM, post CTA, profile CTA, call attempt, etc.

### Conversation

A communication thread. Conversations are tracked independently from channel activity. A person can have channel activity without a conversation having started.

## 3. Channel model

Initial channels:

- Email
- LinkedIn
- Instagram
- Reddit
- Social content
- Website / first-party
- Phone (future)

Email is automated with human approval of the personalized sequence.

LinkedIn, Instagram and Reddit are expected to use Composio where the connected account exposes the required capability. Humans handle actions that are unavailable, paid, restricted, or materially revenue-sensitive.

TinyFish is for research/enrichment, not campaign execution.

Hermes is an operator/agent that can use MCP/tooling to perform work; Sentinel Layer remains the system of record.

## 4. Human / AI boundary

AI:

- Researches public information.
- Finds and structures evidence.
- Scores/ranks using deterministic rules where the playbook defines rules.
- Recommends who to contact, why now, channel sequence, personalization angle and follow-up.
- Drafts personalized messages/sequences.

Human/operator:

- Approves the outreach sequence.
- Handles consequential revenue actions.
- Can edit/stop/re-route any sequence.
- Makes the final judgment on cross-contact/company decisions.

System:

- Persists state.
- Executes approved email automation.
- Executes Composio-supported actions after approval.
- Tracks interactions and attribution.
- Enforces suppression/safety rules.

## 5. Company-level campaign model

A company can participate in several campaigns simultaneously.

Recommended hierarchy:

```
Campaign
  -> Campaign Batch
      -> Company Enrollment
          -> Decision Makers
              -> Touchpoints
```

A monthly campaign is the strategic container. Batches/lists are the operational unit used initially. The design must also support future continuous monthly operation.

## 6. Contact progression

Contact state is about the person, not a single channel.

Suggested state:

```
not_contacted
active
awaiting_reply
replied
follow_up_due
meeting
closed
suppressed
```

Channel activity is stored separately, e.g.:

```
email: awaiting_reply
linkedin: not_contacted
reddit: warmed
```

Social warming is optional. It is a recommendation signal, not a prerequisite to a DM.

## 7. Company/contact suppression

Suppression has at least three scopes:

- Channel-specific
- Campaign-specific
- Global

A personal opt-out from one contact suppresses that contact according to the stated scope. A human reviews whether other decision makers at the company should be contacted.

A clear company-wide "do not contact anyone" instruction suppresses the company.

## 8. Multi-touch attribution principle

Do not force a single winning channel.

Persist the complete chronological/causal journey:

```
strategy
 -> content / post
 -> CTA
 -> touchpoint
 -> website event
 -> conversation
 -> recommendation
 -> meeting
```

Numerical attribution models are reporting views, not the source-of-truth lineage.

The initial system should prioritize journey reconstruction. First-touch/last-touch/multi-touch models can be added later.

## 9. Meeting objective

The current optimization target is `meeting_booked`.

Supporting signals include:

- Conversations
- CTA clicks
- Meeting-page visits
- First-party website behavior
- Social warming
- Buying-intent signals

Generic impressions and weak engagement should not dominate recommendations.

## 10. Deferred work

Do not build now:

- Automatic calling/voice agents
- Complex revenue attribution models
- Fully autonomous social outreach
- Person-level public-platform impression tracking where the platform does not legitimately provide identity
- Advanced ML prediction models
- Autonomous sequence optimization without operator approval

## 11. Design rule

Never introduce a new channel-specific data model when the capability can be represented by the canonical Company -> Decision Maker -> Campaign -> Touchpoint -> Conversation -> Event structure.
