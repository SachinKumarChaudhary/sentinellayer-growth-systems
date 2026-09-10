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
              (SELECT count(*) FROM intelligence.company_facts) AS company_facts,
              (SELECT count(*) FROM intelligence.company_scores) AS scored_companies,
              (SELECT count(*) FROM growth.decision_maker_contact_methods cm
                WHERE cm.channel = 'email') AS dm_email_candidates,
              (SELECT count(*) FROM growth.decision_maker_contact_methods cm
                WHERE cm.channel = 'email'
                  AND lower(coalesce(cm.verification_status, '')) IN ('verified', 'deliverable', 'valid')) AS verified_dm_emails
            """
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("metrics query returned no row")
        keys = [
            "companies", "enriched_companies", "evidence", "decision_makers",
            "intent_signals", "company_facts", "scored_companies",
            "dm_email_candidates", "verified_dm_emails",
        ]
        metrics = dict(zip(keys, row, strict=True))
        metrics["remaining_companies"] = max(metrics["companies"] - metrics["enriched_companies"], 0)

        cur.execute(
            """
            WITH enriched AS (
              SELECT DISTINCT company_id
              FROM intelligence.enrichment_runs
              WHERE status = 'completed'
            ),
            ev AS (
              SELECT company_id,
                     count(*) AS evidence,
                     count(*) FILTER (WHERE source_url IS NOT NULL AND btrim(source_url) <> '') AS evidence_with_url,
                     count(*) FILTER (WHERE confidence >= 0.8) AS high_conf_evidence,
                     avg(confidence) AS avg_evidence_conf
              FROM intelligence.evidence
              GROUP BY company_id
            ),
            dm AS (
              SELECT company_id, count(*) AS dms
              FROM growth.decision_makers
              GROUP BY company_id
            ),
            dm_ev AS (
              SELECT company_id, count(DISTINCT decision_maker_id) AS dm_with_evidence
              FROM intelligence.evidence
              WHERE decision_maker_id IS NOT NULL
                AND source_url IS NOT NULL
                AND btrim(source_url) <> ''
              GROUP BY company_id
            ),
            intent AS (
              SELECT company_id,
                     count(*) AS intent_signals,
                     count(*) FILTER (WHERE evidence_id IS NOT NULL) AS intent_with_evidence,
                     count(*) FILTER (WHERE signal_date IS NOT NULL) AS intent_dated
              FROM intelligence.intent_signals
              GROUP BY company_id
            ),
            dm_email AS (
              SELECT d.company_id,
                     count(*) FILTER (WHERE cm.channel = 'email') AS email_candidates,
                     count(*) FILTER (WHERE cm.channel = 'email'
                       AND lower(coalesce(cm.verification_status, '')) IN ('verified', 'deliverable', 'valid')) AS verified_emails
              FROM growth.decision_makers d
              JOIN growth.decision_maker_contact_methods cm ON cm.decision_maker_id = d.decision_maker_id
              GROUP BY d.company_id
            )
            SELECT
              count(*) AS enriched,
              count(*) FILTER (WHERE cf.company_id IS NOT NULL) AS with_facts,
              count(*) FILTER (WHERE coalesce(ev.evidence, 0) > 0) AS with_evidence,
              count(*) FILTER (WHERE coalesce(ev.evidence, 0) >= 2) AS with_2plus_evidence,
              count(*) FILTER (WHERE coalesce(ev.evidence_with_url, 0) > 0) AS evidence_url_covered,
              count(*) FILTER (WHERE coalesce(ev.high_conf_evidence, 0) > 0) AS with_high_conf_evidence,
              count(*) FILTER (WHERE coalesce(dm.dms, 0) > 0) AS with_dm,
              count(*) FILTER (WHERE coalesce(dm.dms, 0) >= 2) AS with_2plus_dm,
              count(*) FILTER (WHERE coalesce(dm_ev.dm_with_evidence, 0) > 0) AS with_dm_evidence,
              count(*) FILTER (WHERE coalesce(i.intent_signals, 0) > 0) AS with_intent,
              count(*) FILTER (WHERE coalesce(i.intent_with_evidence, 0) > 0) AS intent_evidence_linked,
              count(*) FILTER (WHERE coalesce(i.intent_dated, 0) > 0) AS intent_dated,
              count(*) FILTER (WHERE coalesce(dm_email.email_candidates, 0) > 0) AS with_dm_email,
              count(*) FILTER (WHERE coalesce(dm_email.verified_emails, 0) > 0) AS with_verified_dm_email,
              count(*) FILTER (WHERE cs.company_id IS NOT NULL) AS with_score,
              coalesce(avg(ev.avg_evidence_conf) FILTER (WHERE ev.avg_evidence_conf IS NOT NULL), 0) AS avg_evidence_conf
            FROM enriched e
            LEFT JOIN intelligence.company_facts cf ON cf.company_id = e.company_id
            LEFT JOIN ev ON ev.company_id = e.company_id
            LEFT JOIN dm ON dm.company_id = e.company_id
            LEFT JOIN dm_ev ON dm_ev.company_id = e.company_id
            LEFT JOIN intent i ON i.company_id = e.company_id
            LEFT JOIN dm_email ON dm_email.company_id = e.company_id
            LEFT JOIN intelligence.company_scores cs ON cs.company_id = e.company_id
            """
        )
        quality_row = cur.fetchone()
        if quality_row is None:
            raise RuntimeError("quality query returned no row")
        quality_keys = [
            "enriched", "with_facts", "with_evidence", "with_2plus_evidence",
            "evidence_url_covered", "with_high_conf_evidence", "with_dm",
            "with_2plus_dm", "with_dm_evidence", "with_intent",
            "intent_evidence_linked", "intent_dated", "with_dm_email",
            "with_verified_dm_email", "with_score", "avg_evidence_conf",
        ]
        quality = dict(zip(quality_keys, quality_row, strict=True))

        cur.execute(
            """
            WITH enriched AS (
              SELECT DISTINCT company_id
              FROM intelligence.enrichment_runs
              WHERE status = 'completed'
            ),
            ev AS (
              SELECT company_id, count(*) AS evidence,
                     count(*) FILTER (WHERE source_url IS NOT NULL AND btrim(source_url) <> '') AS evidence_with_url,
                     avg(confidence) AS avg_evidence_conf
              FROM intelligence.evidence GROUP BY company_id
            ),
            dm AS (
              SELECT company_id, count(*) AS dms FROM growth.decision_makers GROUP BY company_id
            ),
            dm_ev AS (
              SELECT company_id, count(DISTINCT decision_maker_id) AS dm_with_evidence
              FROM intelligence.evidence
              WHERE decision_maker_id IS NOT NULL AND source_url IS NOT NULL AND btrim(source_url) <> ''
              GROUP BY company_id
            ),
            intent AS (
              SELECT company_id, count(*) AS intent_signals,
                     count(*) FILTER (WHERE evidence_id IS NOT NULL) AS intent_with_evidence,
                     count(*) FILTER (WHERE signal_date IS NOT NULL) AS intent_dated
              FROM intelligence.intent_signals GROUP BY company_id
            ),
            dm_email AS (
              SELECT d.company_id,
                     count(*) FILTER (WHERE cm.channel = 'email') AS email_candidates,
                     count(*) FILTER (WHERE cm.channel = 'email'
                       AND lower(coalesce(cm.verification_status, '')) IN ('verified', 'deliverable', 'valid')) AS verified_emails
              FROM growth.decision_makers d
              JOIN growth.decision_maker_contact_methods cm ON cm.decision_maker_id = d.decision_maker_id
              GROUP BY d.company_id
            )
            SELECT c.id, c.name, c.domain,
                   coalesce(ev.evidence, 0), coalesce(ev.evidence_with_url, 0),
                   coalesce(ev.avg_evidence_conf, 0), coalesce(dm.dms, 0),
                   coalesce(dm_ev.dm_with_evidence, 0), coalesce(i.intent_signals, 0),
                   coalesce(i.intent_with_evidence, 0), coalesce(i.intent_dated, 0),
                   coalesce(dm_email.email_candidates, 0), coalesce(dm_email.verified_emails, 0),
                   (cf.company_id IS NOT NULL), (cs.company_id IS NOT NULL)
            FROM enriched e
            JOIN public.companies c ON c.id = e.company_id
            LEFT JOIN intelligence.company_facts cf ON cf.company_id = e.company_id
            LEFT JOIN intelligence.company_scores cs ON cs.company_id = e.company_id
            LEFT JOIN ev ON ev.company_id = e.company_id
            LEFT JOIN dm ON dm.company_id = e.company_id
            LEFT JOIN dm_ev ON dm_ev.company_id = e.company_id
            LEFT JOIN intent i ON i.company_id = e.company_id
            LEFT JOIN dm_email ON dm_email.company_id = e.company_id
            ORDER BY c.id
            """
        )
        quality_companies = []
        for r in cur.fetchall():
            quality_companies.append({
                "id": r[0], "name": r[1], "domain": r[2], "evidence": r[3],
                "evidence_with_url": r[4], "avg_evidence_conf": float(r[5] or 0),
                "decision_makers": r[6], "dm_with_evidence": r[7],
                "intent_signals": r[8], "intent_with_evidence": r[9],
                "intent_dated": r[10], "dm_email_candidates": r[11],
                "verified_dm_emails": r[12], "has_facts": bool(r[13]),
                "has_score": bool(r[14]),
            })

        cur.execute(
            """
            WITH latest AS (
              SELECT DISTINCT ON (er.company_id)
                er.company_id, er.status, er.completed_at, er.started_at
              FROM intelligence.enrichment_runs er
              ORDER BY er.company_id, er.completed_at DESC NULLS LAST, er.started_at DESC
            )
            SELECT c.id, c.name, c.domain, latest.status, latest.completed_at, latest.started_at,
              (SELECT count(*) FROM intelligence.evidence e WHERE e.company_id = c.id),
              (SELECT count(*) FROM growth.decision_makers dm WHERE dm.company_id = c.id),
              (SELECT count(*) FROM intelligence.intent_signals i WHERE i.company_id = c.id)
            FROM public.companies c
            JOIN latest ON latest.company_id = c.id
            ORDER BY COALESCE(latest.completed_at, latest.started_at) DESC NULLS LAST
            LIMIT 30
            """
        )
        recent_companies = [
            {"id": r[0], "name": r[1], "domain": r[2], "status": r[3],
             "completed_at": r[4].isoformat() if r[4] else None,
             "started_at": r[5].isoformat() if r[5] else None,
             "evidence": r[6], "decision_makers": r[7], "intent_signals": r[8]}
            for r in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT er.company_id, c.name, er.provider, er.status, er.started_at, er.completed_at
            FROM intelligence.enrichment_runs er
            JOIN public.companies c ON c.id = er.company_id
            ORDER BY COALESCE(er.completed_at, er.started_at) DESC NULLS LAST
            LIMIT 30
            """
        )
        recent_runs = [
            {"company_id": r[0], "company_name": r[1], "provider": r[2], "status": r[3],
             "started_at": r[4].isoformat() if r[4] else None,
             "completed_at": r[5].isoformat() if r[5] else None}
            for r in cur.fetchall()
        ]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "quality": quality,
        "quality_companies": quality_companies,
        "recent_companies": recent_companies,
        "recent_runs": recent_runs,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
