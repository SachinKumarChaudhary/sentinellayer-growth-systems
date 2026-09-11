"""Import the immutable ScraperCity company CSV into growth.company_source_data.

The command validates the complete CSV before any database write. It preserves
all source fields and the complete row as raw_row_json. It expects DATABASE_URL
(or SUPABASE_DB_URL) to be a Postgres connection string.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED_COLUMNS = [
    "domain", "merchant_name", "description", "platform", "plan", "rank",
    "estimated_monthly_sales", "estimated_monthly_visits", "estimated_monthly_pageviews",
    "employee_count", "country_code", "state", "city", "street_address", "zip",
    "emails", "phones", "categories", "technologies", "installed_apps_names",
    "installed_apps_count", "products_sold", "theme", "currency", "status", "facebook",
    "facebook_url", "instagram", "instagram_url", "tiktok", "tiktok_url", "youtube",
    "youtube_url", "linkedin_account", "linkedin_url", "twitter", "twitter_url",
    "pinterest", "pinterest_url", "whatsapp", "domain_url", "created",
]

SOURCE_FILE = "Store Leads Shopify - US - ScraperCity.csv"


def normalize_domain(value: str) -> str:
    v = (value or "").strip().lower()
    if not v:
        return ""
    if "://" in v:
        v = urlsplit(v).hostname or v
    else:
        v = v.split("/", 1)[0]
    v = v.removeprefix("www.")
    return v.rstrip(".")


def clean_int(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return int(float(re.sub(r"[^0-9.-]", "", v)))


def clean_num(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return float(re.sub(r"[^0-9.-]", "", v))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--source-file", default=SOURCE_FILE)
    args = ap.parse_args()

    with args.csv.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames or []
        if columns != EXPECTED_COLUMNS:
            missing = [c for c in EXPECTED_COLUMNS if c not in columns]
            extra = [c for c in columns if c not in EXPECTED_COLUMNS]
            raise SystemExit(f"CSV schema mismatch; missing={missing}; extra={extra}")
        rows = list(reader)

    if len(rows) != 1200:
        raise SystemExit(f"Expected 1200 rows, found {len(rows)}")

    normalized = []
    seen = set()
    for row_no, row in enumerate(rows, 1):
        domain = normalize_domain(row["domain"])
        if not domain:
            raise SystemExit(f"Row {row_no}: missing domain")
        if domain in seen:
            raise SystemExit(f"Row {row_no}: duplicate normalized domain {domain}")
        seen.add(domain)
        normalized.append((row_no, domain, row))

    if args.dry_run:
        print(json.dumps({"rows": len(rows), "columns": len(columns), "unique_domains": len(seen), "dry_run": True}))
        return 0

    import psycopg
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL or DATABASE_URL is required")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, lower(regexp_replace(domain, '^www\\\\.', '')) FROM public.companies")
            companies = {normalize_domain(d): cid for cid, d in cur.fetchall()}
            missing = sorted(seen - set(companies))
            if missing:
                raise SystemExit(f"{len(missing)} CSV domains do not match public.companies: {missing[:10]}")

            payload = []
            for row_no, domain, row in normalized:
                payload.append({
                    "company_id": companies[domain], "normalized_domain": domain,
                    "source_file": args.source_file, "source_row_number": row_no,
                    **{k: row[k] or None for k in EXPECTED_COLUMNS if k not in {"rank", "estimated_monthly_sales", "estimated_monthly_visits", "estimated_monthly_pageviews", "employee_count", "installed_apps_count"}},
                    "rank": clean_int(row["rank"]), "estimated_monthly_sales": clean_num(row["estimated_monthly_sales"]),
                    "estimated_monthly_visits": clean_num(row["estimated_monthly_visits"]), "estimated_monthly_pageviews": clean_num(row["estimated_monthly_pageviews"]),
                    "employee_count": clean_int(row["employee_count"]), "installed_apps_count": clean_int(row["installed_apps_count"]),
                    "raw_row_json": row,
                })

            cols = list(payload[0].keys())
            sql = f"INSERT INTO growth.company_source_data ({', '.join(cols)}) VALUES ({', '.join('%s' for _ in cols)}) ON CONFLICT (company_id) DO UPDATE SET " + ', '.join(f"{c}=EXCLUDED.{c}" for c in cols if c != 'id')
            cur.executemany(sql, [tuple(p[c] if c != "raw_row_json" else json.dumps(p[c]) for c in cols) for p in payload])
            cur.execute("SELECT count(*) FROM growth.company_source_data WHERE source_file = %s", (args.source_file,))
            count = cur.fetchone()[0]
            if count != 1200:
                raise SystemExit(f"Post-import reconciliation failed: {count} rows")
        conn.commit()
    print(json.dumps({"rows_imported": 1200, "source_file": args.source_file, "status": "ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
