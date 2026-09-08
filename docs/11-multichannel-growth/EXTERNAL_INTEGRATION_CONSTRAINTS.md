# Sentinel Layer — External Integration Constraints

**Status:** Canonical implementation constraint  
**Date:** 2026-09-08  
**Sources checked:** current public TinyFish and Composio documentation on 2026-09-08.

## 1. TinyFish current limits

TinyFish Search:
- Free
- 30 requests/minute
- 500 requests/hour

TinyFish Fetch:
- Free
- 150 URLs/minute
- 1,000 URLs/day

TinyFish Agent:
- 2 concurrent runs
- Metered

TinyFish Browser:
- 5 concurrent sessions
- Metered

### Application policy

For enrichment:
- Treat Search and Fetch as the primary web-research resource.
- Use them heavily within the limits.
- Maintain local/database research state and caching.
- Do not repeatedly fetch unchanged URLs.
- Schedule calls through a rate-limit-aware queue.
- Keep Search and Fetch budgets independently.
- Do not use Agent/Browser for routine enrichment unless a separate decision explicitly authorizes the cost.

## 2. Composio current API model

Composio provides:
- project API-key authentication
- SDKs and REST APIs
- Tool Router sessions for agents
- tool search/schema discovery
- connected-account management
- OAuth/API-key/bearer/basic authentication depending on toolkit
- tool execution through API/SDK
- MCP/meta tools for agents

Current public Composio documentation states project/API organization keys authenticate requests, and plan-dependent API rate limits are currently 2,000–10,000 requests/minute.

Connected accounts hold the provider credentials/tokens and Composio manages OAuth refresh for managed OAuth connections.

## 3. LinkedIn toolkit currently observed

Current public toolkit version shown by Composio: 20260826_00.

Observed tools include:
- create article/URL share
- create comment on LinkedIn post
- create LinkedIn post
- create video post
- get company info
- get person profile
- get post content
- list reactions
- share statistics
- organization/page statistics
- image/video operations
- network size

**Important:** the public toolkit catalog currently inspected did not list a direct LinkedIn DM-send tool.

Therefore:
- Do not design or claim a LinkedIn DM API action until the connected Composio project/account actually exposes one.
- The LinkedIn channel adapter must support a capability discovery step.
- If DM is unavailable, create an operator task rather than silently failing or inventing an action.
- Re-check the actual connected tool catalog during implementation because toolkit versions can change.

## 4. Instagram toolkit currently observed

Current public toolkit version shown by Composio: 20260819_00.

Observed capabilities include:
- list/fetch conversations
- list messages
- send text message
- send image
- create/publish media
- comments/replies
- user/media insights
- user info
- profile/message operations

Instagram toolkit support is for Business/Creator accounts, not personal accounts.

Instagram DM behavior is constrained by Meta's messaging window; Composio's documentation specifically notes a 24-hour reply window for certain DM scenarios.

## 5. Reddit toolkit currently observed

Current public toolkit version shown by Composio: 20260826_00.

Observed tools include:
- create/edit/delete posts and comments
- post comments
- retrieve posts/comments
- subreddit search
- cross-subreddit search
- user information
- subreddit rules/flairs

The public toolkit list inspected did not show a direct private-DM send tool.

Therefore the same capability-discovery/fallback policy applies:
- use a supported Composio action when present
- otherwise route to operator/manual workflow
- never invent a Reddit DM capability

## 6. Composio agent operating model

Recommended pattern:

```
Hermes / other agent
  -> Tool Router session
  -> COMPOSIO_SEARCH_TOOLS
  -> discover exact tool
  -> COMPOSIO_GET_TOOL_SCHEMAS
  -> execute exact tool
```

For deterministic backend execution:

```
Sentinel Layer
  -> channel adapter
  -> Composio API/SDK
  -> connected account
  -> platform
```

Store the exact tool slug and toolkit version used on execution records.

## 7. Apify multiple-key policy

The system will support multiple Apify API keys.

Rules:
- Actual keys are stored as deployment secrets/secret-manager values, not plaintext in application tables.
- Supabase stores only credential references and pool state.
- Each key is represented by an `ops.provider_pool_member`.
- Selection prefers healthy/non-cooled-down keys.
- If a key returns a provider rate-limit/quota response, mark it cooled down and rotate to the next healthy key.
- Persist provider error and selection metadata.
- Do not rotate aggressively on generic failures that are unrelated to quota.
- If all keys are exhausted, queue the work rather than creating an unbounded retry loop.
- Never log raw API keys.

## 8. QEV / Email Hippo

Use API-key based integrations behind an email-verification adapter.

The adapter returns normalized:
- status
- provider
- checked_at
- reason
- confidence

The campaign layer never depends on a provider-specific response vocabulary.

## 9. Enrichment tool-selection policy

Default order:

```
Existing database facts
  -> cached evidence
  -> free local/domain oracles
  -> TinyFish Search/Fetch
  -> AI research synthesis
  -> QEV / Email Hippo
  -> Apify email finding when useful
  -> operator/manual fallback
```

This order is optimized for information value and cost, not for using every tool on every company.

## 10. Evidence rules

AI research is accepted only as evidence when it retains:
- source URL
- claim
- observed time
- event date when relevant
- source/provider
- confidence

A source being public does not mean it is immutable or permanently accessible. Preserve the URL and the extracted evidence snapshot needed to audit the claim.

## 11. Capability revalidation

At integration startup or before a new action class is enabled:
- query the connected Composio tool catalog
- record available tool slugs
- record toolkit version
- record connection status
- verify required scopes/capabilities
- fail closed for unsupported actions

Do not treat the public documentation as a substitute for verifying the actual connected account.
