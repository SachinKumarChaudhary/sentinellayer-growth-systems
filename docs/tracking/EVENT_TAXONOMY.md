# Tracking Event Taxonomy

## Canonical event types

### Email/content
- `email_opened`
- `link_clicked`
- `asset_clicked`
- `asset_viewed`
- `asset_progressed`
- `loom_started`
- `loom_progressed`
- `brief_viewed`
- `brief_progressed`

### Website/product
- `landing_viewed`
- `docs_viewed`
- `pricing_viewed`
- `diagnostic_started`
- `diagnostic_completed`
- `trial_signup`
- `sdk_installed`
- `evaluate_called`

### Session
- `session_started`
- `session_resumed`
- `session_ended`

## Event properties

Common payload fields should use stable names and contain only the minimum data needed to interpret the observation.

Examples:

```json
{
  "event_type": "pricing_viewed",
  "payload": {
    "path": "/pricing",
    "duration_ms": 18400
  }
}
```

```json
{
  "event_type": "loom_progressed",
  "payload": {
    "percent": 75,
    "asset_id": "opaque-asset-id"
  }
}
```

## Trust labels

Tracking implementation attaches `automation_classification` outside the public TrackingEvent contract:

- `automated`
- `human_candidate`
- `unknown`

The classification describes traffic characteristics, not identity proof.

## Promotion rules

Tracking does not itself promote P2→P1 or create opportunities. Existing Intent logic decides how behavior contributes to priority. An event may be high-confidence evidence without being commercially decisive.
