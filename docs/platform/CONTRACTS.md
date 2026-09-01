# Contract Registry

The JSON Schemas under `schemas/` are authoritative for machine validation.

| Contract | Producer | Consumers |
|---|---|---|
| AccountRef | Intelligence | Campaign, Platform tests |
| PersonRef | Intelligence | Campaign, Mail boundary |
| IntentSnapshot | Intelligence | Campaign |
| CampaignEnrollment | Campaign / persistence boundary | Campaign, Mail |
| RenderedSendTreatment | Campaign | Mail |
| SendRequest | Platform/Mail boundary | Mail |
| ProviderOutcome | Mail | Tracking, Conversation, Analytics |
| TrackingEvent | Tracking | Conversation, Analytics |
| ConversationHandoff | Conversation | Sales, Analytics |
| SalesHandoff | Sales | Analytics |
| AttributionContext | Platform/Analytics boundary | Analytics |

Every contract requires an explicit version, stable identity fields, ownership, lifecycle semantics where applicable, validation rules, compatibility policy, and integration tests. Breaking changes require explicit versioning or migration strategy.
