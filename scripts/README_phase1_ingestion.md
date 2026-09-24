# ScraperCity Phase 1 ingestion

The ingestion runner sends the ScraperCity Shopify export through the Phase 1 adapter, deterministic pipeline, duplicate adjudication, and durable repository.

## Dry run

Dry run requires no database credentials:

```bash
python scripts/ingest_scrapercity_phase1.py \
  --csv "Store Leads Shopify - US - ScraperCity.csv" \
  --dry-run
```

Optional `--limit N` processes only the first N rows.

## Live ingestion

Live mode requires a PostgreSQL connection string in `SUPABASE_DB_URL`. The runner:

1. validates the CSV has exactly 42 columns;
2. assigns the stable ScraperCity source key from the one-based source row number;
3. creates an immutable observation ID from source identity + raw fingerprint;
4. loads existing immutable observations for exact duplicate adjudication;
5. processes the complete batch through Phase 1;
6. persists observations, processing state, findings, canonical projection, quarantine, and handoffs through `Phase1Repository`.

The runner does not modify `public.companies` or `growth.company_source_data`.

Do not run live ingestion until the dry-run counts have been reviewed against the expected 1,200-row source.
