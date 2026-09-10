from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard" / "data.json"
DB_URL = os.environ["SUPABASE_DATABASE_URL"]


def main() -> None:
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              (SELECT count(*) FROM public.companies) AS companies,
              (SELECT count(DISTINCT er.company_id)
                 FROM intelligence.enrichment_runs er
                WHERE er.status = 'completed') AS enriched_companies,
              (SELECT count(*) FROM intelligence.evidence) AS evidence,
              (SELECT count(*) FROM growth.decision_makers) AS decision_makers,
              (SELECT count(*) FROM intelligence.intent_signals) AS intent_signals,
              (SELECT count(*) FROM intelligence.company_facts) AS company_facts
            """
        )
        metrics_row = cur.fetchone()
        if metrics_row is None:
            raise RuntimeError("metrics query returned no row")
        keys = ["companies", "enriched_companies", "evidence", "decision_makers", "intent_signals", "company_facts"]
        metrics = dict(zip(keys, metrics_row, strict=True))
        metrics["remaining_companies"] = max(metrics["companies"] - metrics["enriched_companies"], 0)

        cur.execute(
            """
            WITH latest AS (
              SELECT DISTINCT ON (er.company_id)
                er.company_id, er.status, er.completed_at, er.started_at
              FROM intelligence.enrichment_runs er
              ORDER BY er.company_id, er.completed_at DESC NULLS LAST, er.started_at DESC
            )
            SELECT
              c.id,
              c.name,
              c.domain,
              latest.status,
              latest.completed_at,
              latest.started_at,
              (SELECT count(*) FROM intelligence.evidence e WHERE e.company_id = c.id) AS evidence,
              (SELECT count(*) FROM growth.decision_makers dm WHERE dm.company_id = c.id) AS decision_makers,
              (SELECT count(*) FROM intelligence.intent_signals i WHERE i.company_id = c.id) AS intent_signals
            FROM public.companies c
            JOIN latest ON latest.company_id = c.id
            ORDER BY COALESCE(latest.completed_at, latest.started_at) DESC NULLS LAST
            LIMIT 30
            """
        )
        recent_companies = [
            {
                "id": row[0],
                "name": row[1],
                "domain": row[2],
                "status": row[3],
                "completed_at": row[4].isoformat() if row[4] else None,
                "started_at": row[5].isoformat() if row[5] else None,
                "evidence": row[6],
                "decision_makers": row[7],
                "intent_signals": row[8],
            }
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT
              er.company_id,
              c.name,
              er.provider,
              er.status,
              er.started_at,
              er.completed_at
            FROM intelligence.enrichment_runs er
            JOIN public.companies c ON c.id = er.company_id
            ORDER BY COALESCE(er.completed_at, er.started_at) DESC NULLS LAST
            LIMIT 30
            """
        )
        recent_runs = [
            {
                "company_id": row[0],
                "company_name": row[1],
                "provider": row[2],
                "status": row[3],
                "started_at": row[4].isoformat() if row[4] else None,
                "completed_at": row[5].isoformat() if row[5] else None,
            }
            for row in cur.fetchall()
        ]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "recent_companies": recent_companies,
        "recent_runs": recent_runs,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
