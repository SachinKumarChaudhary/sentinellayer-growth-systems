"""Reconcile growth.company_source_data against the source CSV and public.companies."""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from urllib.parse import urlsplit


def norm(value: str) -> str:
    value = (value or "").strip().lower()
    if "://" in value:
        value = urlsplit(value).hostname or value
    else:
        value = value.split("/", 1)[0]
    return value.removeprefix("www.").rstrip(".")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    csv_domains = {norm(row["domain"]) for row in rows}
    import psycopg

    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("SUPABASE_DB_URL or DATABASE_URL is required")
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from public.companies")
        companies = cur.fetchone()[0]
        cur.execute("select count(*) from growth.company_source_data")
        source_rows = cur.fetchone()[0]
        cur.execute("select normalized_domain from growth.company_source_data")
        db_domains = {row[0] for row in cur.fetchall()}
        print({
            "csv_rows": len(rows),
            "csv_unique_domains": len(csv_domains),
            "public_companies": companies,
            "source_rows": source_rows,
            "missing_from_source": len(csv_domains - db_domains),
            "extra_in_source": len(db_domains - csv_domains),
        })
        if (
            len(rows) != 1200
            or len(csv_domains) != 1200
            or companies != 1200
            or source_rows != 1200
            or csv_domains != db_domains
        ):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
