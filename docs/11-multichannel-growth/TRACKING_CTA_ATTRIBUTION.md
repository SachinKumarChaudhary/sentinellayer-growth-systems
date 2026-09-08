# Sentinel Layer — CTA, Tracking and Attribution Design

**Status:** Canonical design baseline  
**Date:** 2026-09-08

## 1. Objective

Track how companies move from outreach and content into first-party interaction, conversation and meetings.

The system should explain how channels cooperate rather than declaring one channel the winner.

## 2. Canonical lineage

```
Strategy
  -> Campaign
  -> Content / Message
  -> Placement
  -> CTA
  -> Touchpoint
  -> Event
  -> Conversation
  -> Meeting
```

All available canonical IDs should be preserved.

## 3. CTA model

A CTA is a versioned business object.

Examples:

- Run the security diagnostic
- See the session-risk demo
- Book 15 minutes
- See how Sentinel Layer works

A CTA can be reused across placements.

## 4. Placement model

A placement identifies where the CTA was presented.

Examples:

- linkedin_profile
- linkedin_post
- linkedin_comment
- linkedin_dm
- instagram_profile
- instagram_post
- instagram_dm
- reddit_post
- reddit_comment
- reddit_dm
- email
- website
- future_phone

CTA and placement are distinct dimensions.

## 5. First-party links

Public URLs should use branded, human-readable paths where practical.

Preferred initial approach:

```
https://sentinellayer.in/go/<opaque-token>
```

or an equivalent branded subdomain if operationally useful.

Do not put raw email addresses, names or sensitive identifiers in URLs.

The token resolves server-side to attribution metadata.

A separate tracking domain is **not required** for the initial implementation.

## 6. Social reputation principle

Do not automatically inject ugly opaque links into LinkedIn profile text or every public social post.

For public content, prefer the branded primary-domain destination.

Use person-specific attribution when it is legitimate and useful, especially for 1:1 outreach.

For public profiles/posts, placement/content/campaign attribution may be sufficient when person-level identity is not available.

## 7. Tracking events

Existing first-party events remain canonical where applicable:

- landing_viewed
- docs_viewed
- pricing_viewed
- diagnostic_started
- diagnostic_completed
- trial_signup
- sdk_installed
- evaluate_called
- session_started/resumed/ended

Additional outreach/social event families can include:

- touchpoint_created
- touchpoint_sent
- touchpoint_delivered
- touchpoint_failed
- profile_cta_clicked
- post_cta_clicked
- social_message_sent
- social_message_received
- social_message_replied
- call_attempted
- call_connected
- call_completed

Do not create identity claims from platform impressions that the platform does not legitimately expose.

## 8. Attribution context

At minimum preserve when known:

- account/company
- person
- campaign
- campaign enrollment
- strategy
- offer
- message
- CTA
- sequence
- experiment / variant
- send / touchpoint
- channel
- placement
- content / post / profile
- timestamp
- source
- confidence

## 9. Person-level vs placement-level attribution

Use three levels:

### Exact-person attribution

Use when a legitimate first-party or provider signal gives strong identity.

### Placement attribution

LinkedIn profile, LinkedIn post, Reddit post, email, etc.

### Campaign/content attribution

Strategy, campaign, CTA, content, experiment.

Never invent person identity from IP address alone or weak profile similarities.

## 10. Attribution philosophy

The source of truth is the interaction journey.

Example:

```
LinkedIn post
 -> profile
 -> CTA
 -> website
 -> email
 -> reply
 -> follow-up
 -> meeting
```

This whole path should be reconstructable.

Numerical models may later calculate first-touch, last-touch or multi-touch credit, but these are reporting interpretations.

## 11. Meeting conversion

`meeting_booked` is the current primary conversion event.

Supporting events:

- conversations
- CTA clicks
- meeting-page visits
- diagnostics
- qualified first-party activity

Do not optimize the system around opens or generic impressions.

## 12. Data-quality rules

Every event must be idempotent.

Every event should preserve provenance.

Unknown event names may be ingested only under a generic envelope; downstream scoring must ignore unknown events until registered.

No direct public browser writes to operational tracking tables.

## 13. Retention/security

Continue the existing principles:

- opaque public tokens
- no raw email in public URLs
- no raw IP persistence unless explicitly required and protected
- controlled first-party server ingestion
- RLS
- deterministic deduplication
- retention/deletion policy

## 14. Domain recommendation

For the initial system, use the existing primary domain:

```
sentinellayer.in
```

with a branded `/go/` path or a branded tracking subdomain later.

Do not purchase another domain solely for CTA tracking unless future deliverability/brand-separation requirements independently justify it.
