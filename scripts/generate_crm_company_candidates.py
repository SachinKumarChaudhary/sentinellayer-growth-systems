from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import psycopg

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.crm.migration import build_operational_sheet_staged_rows, load_source_rows, normalize_domain, profile_source

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "proton.me", "protonmail.com", "rediffmail.com", "yahoo.co.in",
}

def normalized_company(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())
def _business_email_domains(row: dict[str, Any]) -> set[str]:
    emails = re.findall(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        row.get("Email") or "",
    )
    return {
        domain for domain in (e.split("@", 1)[1].lower() for e in emails)
        if domain not in FREE_EMAIL_DOMAINS
    }


def candidate_for_row(row: dict[str, Any]) -> dict[str, Any]:
    company = (row.get("company") or "").strip()
    domains = sorted(_business_email_domains(row))
    if len(domains) == 1:
        return {
            "candidate_domain": normalize_domain(domains[0]),
            "domain_source": "business_email_domain",
            "resolution_status": "AUTO_CANDIDATE",
            "provenance": {"business_email_domains": domains},
        }
    if len(domains) > 1:
        return {
            "candidate_domain": None,
            "domain_source": "multiple_business_email_domains",
            "resolution_status": "REVIEW",
            "provenance": {"business_email_domains": domains},
        }
    return {
        "candidate_domain": None,
        "domain_source": "no_deterministic_business_email_domain",
        "resolution_status": "UNRESOLVED",
        "provenance": {"business_email_domains": []},
    }
def build_candidate_rows(rows: list[dict[str, Any]], *, source_name: str, snapshot_hash: str) -> list[dict[str, Any]]:
    staged = build_operational_sheet_staged_rows(
        source_name=source_name,
        snapshot_hash=snapshot_hash,
        rows=rows,
        importer_version="crm-mvp.sheet.v1",
    )
    candidates: list[dict[str, Any]] = []
    for item in staged:
        if item.disposition not in {"imported", "merged"}:
            continue
        candidate = candidate_for_row(item.raw_row)
        company = str(item.raw_row.get("company") or "").strip()
        candidates.append({
            "source_name": source_name,
            "source_snapshot_hash": snapshot_hash,
            "source_row_number": item.source_row_number,
            "source_company_name": company,
            "normalized_company_name": normalized_company(company),
            **candidate,
            "provenance": {
                **candidate["provenance"],
                "source_row_hash": item.source_row_hash,
                "source_disposition": item.disposition,
                "raw_intent_present": bool(item.raw_row.get("Intent")),
                "raw_status_present": bool(item.raw_row.get("Lead Status")),
            },
        })
    return candidates
def _connection_factory() -> psycopg.Connection[Any]:
    settings = Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required for --apply")
    settings.assert_safe()
    return psycopg.connect(settings.database_url)
def persist_candidates(connection_factory, candidates: list[dict[str, Any]]) -> None:
    with connection_factory() as conn, conn.cursor() as cur:
        for row in candidates:
            cur.execute(
                """
                insert into crm.migration_company_candidates(
                  source_name,source_snapshot_hash,source_row_number,
                  source_company_name,normalized_company_name,candidate_domain,
                  domain_source,resolution_status,provenance
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                on conflict (source_name,source_snapshot_hash,source_row_number)
                do update set
                  source_company_name=excluded.source_company_name,
                  normalized_company_name=excluded.normalized_company_name,
                  candidate_domain=excluded.candidate_domain,
                  domain_source=excluded.domain_source,
                  resolution_status=excluded.resolution_status,
                  provenance=excluded.provenance,
                  updated_at=now()
                """,
                (
                    row["source_name"], row["source_snapshot_hash"], row["source_row_number"],
                    row["source_company_name"], row["normalized_company_name"],
                    row["candidate_domain"], row["domain_source"], row["resolution_status"],
                    json.dumps(row["provenance"], ensure_ascii=False),
                ),
            )
def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sheet company-domain candidates.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", default="sentinellayer-outreach-sheet")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        snapshot = profile_source(source_name=args.name, path=args.source, importer_version="crm-mvp.sheet.v1")
        _, rows = load_source_rows(args.source)
        candidates = build_candidate_rows(rows, source_name=args.name, snapshot_hash=snapshot.file_sha256)
        counts: dict[str, int] = {}
        for row in candidates:
            counts[row["resolution_status"]] = counts.get(row["resolution_status"], 0) + 1
        report = {"source_rows": len(rows), "candidate_rows": len(candidates), "resolution_status": counts, "apply": args.apply}
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if args.apply:
            persist_candidates(_connection_factory, candidates)
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: candidate generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
