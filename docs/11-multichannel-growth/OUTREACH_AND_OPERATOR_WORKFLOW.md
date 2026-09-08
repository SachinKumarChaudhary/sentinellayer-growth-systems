# Sentinel Layer — Outreach, Sequence and Operator Workflow

**Status:** Canonical design baseline  
**Date:** 2026-09-08

## 1. Objective

Use coordinated multichannel outreach to maximize meetings.

The system does not treat channels as competitors. The same company may receive coordinated activity across email, LinkedIn, Instagram, Reddit and later phone.

## 2. Campaign hierarchy

```
Monthly Campaign
  -> Campaign Batch
      -> Company Enrollment
          -> Decision-Maker Targets
              -> Recommended Sequence
                  -> Approved Touchpoints
```

Multiple campaigns may target the same company and different decision makers.

## 3. Sequence generation

For each target contact:

```
company context
+ decision-maker role
+ buying intent
+ available contact surfaces
+ past interactions
+ campaign strategy
+ CTA
      ↓
AI recommendation
      ↓
personalized sequence draft
      ↓
operator review
      ↓
approval
```

AI should explain:

- why this person
- why now
- strongest evidence
- recommended channel order
- recommended message angle
- follow-up timing
- risks/conflicts

## 4. Approval policy

The operator approves the **sequence**, not necessarily every email individually.

After sequence approval:

- Email may execute automatically through the approved sequence.
- Other channels may execute through Composio where the required capability exists and policy allows.
- The operator may stop/edit/re-route any action at any time.

Consequential revenue-sensitive decisions remain human-controlled.

## 5. Channel execution

### Email

Automated execution is supported after human approval.

### LinkedIn / Instagram / Reddit

Use Composio as the channel execution/integration layer for connected accounts.

Expected model:

```
Sentinel Layer
  -> channel adapter
  -> Composio
  -> platform
```

Hermes may access the same capabilities through MCP/tooling.

If a needed action is unavailable, paid, restricted, or requires a manual decision, create an operator task instead of inventing an automation path.

## 6. Follow-up model

Follow-up is primarily contact-centric, not channel-centric.

Example:

```
Contact state:
awaiting_reply

Channel activity:
email = sent
linkedin = not contacted
reddit = warmed

Recommendation:
LinkedIn DM
```

The system should preserve every channel action while keeping one overall contact progression.

## 7. Adaptive sequences

Sequences are recommendations, not immutable calendars.

Example:

```
Email sent
  -> no reply
  -> recommend LinkedIn DM

Email reply
  -> conversation active
  -> stop outbound automation

Negative response
  -> human review

Explicit opt-out
  -> suppression according to scope
```

New evidence can invalidate a previously approved next step.

## 8. Colleague / multi-thread strategy

A company may have multiple decision makers.

The system must show the operator:

- who has been contacted
- what was sent
- who replied
- who opted out
- who remains untouched
- why another decision maker is being recommended

Do not automatically route around a rejection. Another decision maker at the same company requires human review where the first contact has rejected outreach.

## 9. Social nurturing

Social content is optional warming.

It should produce recommendations such as:

```
Recent relevant activity detected
-> "Consider engaging before DM"
```

It must not block direct outreach.

The content system may also provide AI content recommendations based on aggregate buying-intent themes. Scheduled posting remains a separate content-execution concern.

## 10. Recommendation object

Minimum conceptual shape:

```json
{
  "company_id": "...",
  "contact_id": "...",
  "reason": "...",
  "supporting_signals": ["...", "..."],
  "recommended_sequence": [
    "email",
    "linkedin_dm"
  ],
  "personalization_angle": "...",
  "confidence": 0.87,
  "requires_approval": true
}
```

The recommendation is not itself an execution command.

## 11. Contact state

Canonical contact-level states:

- not_contacted
- active
- awaiting_reply
- replied
- follow_up_due
- meeting
- closed
- suppressed

Channel activity is stored as touchpoints/events.

## 12. Company-level state

Suggested company lifecycle:

- unqualified
- qualified
- campaign_ready
- active_outreach
- conversation_active
- meeting
- closed
- suppressed

Company state is not the same as any single contact state.

## 13. Future phone channel

Phone is future work.

When implemented, use a dedicated call model:

```
call_attempt
 -> connected / no_answer / voicemail
 -> call outcome / notes / transcript
 -> conversation context
```

Do not force phone into an email-specific state machine.

## 14. Safety

Never initiate an automated action from tracking alone unless an explicit campaign policy authorizes it.

Behavioral signals are evidence for recommendation.

Explicit suppression always outranks outreach optimization.
