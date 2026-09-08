# TinyFish Search/Fetch integration

SentinelLayer uses TinyFish only as a read-only web research transport for company enrichment.

## Runtime contract

- Search endpoint: `https://api.search.tinyfish.ai`
- Fetch endpoint: `https://api.fetch.tinyfish.ai`
- Authentication: `X-API-Key`
- Application secret: `SL_TINYFISH_API_KEY`
- Search is `GET` with `query` and optional `purpose` query parameters.
- Fetch is `POST` with `urls`, `format`, `links`, `image_links`, and `page_metadata`, plus optional `purpose`.
- Fetch accepts at most 10 URLs per request.
- The adapter exposes no Browser or Agent operation.

## CLI

```text
SL_TINYFISH_API_KEY=... slctl tinyfish search "example.com CEO" --purpose "company enrichment"
SL_TINYFISH_API_KEY=... slctl tinyfish fetch https://example.com/team --purpose "validate leadership evidence"
```

The CLI returns raw Search/Fetch results. It does not label contacts as verified, infer missing facts, assign intent scores, or write to Supabase. Those responsibilities remain with the existing enrichment validation and repository layers.

## Enrichment flow

1. Select 1–3 companies with the existing enrichment repository.
2. Use TinyFish Search to discover public evidence.
3. Fetch only the URLs selected for evidence review.
4. Convert the resulting evidence into the existing `EnrichmentPacket` contract.
5. Validate the packet; contact verification remains a separate provider step.
6. Persist through `EnrichmentRepository.persist_batch(..., provider="tinyfish")`.

This separation prevents a web-research transport from becoming a system-of-record writer or a contact verifier.
