from __future__ import annotations

import argparse
import os
from typing import Any

import psycopg

from sentinellayer_growth_engine.enrichment_quality_gate import (
    is_valid_company_email,
    is_valid_decision_maker,
)


def run(*, fix: bool) -> int:
    database_url = os.environ.get("SL_DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("SL_DATABASE_URL or SUPABASE_DATABASE_URL is required")

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT dm.decision_maker_id, dm.company_id, c.name, c.domain,
                   dm.full_name, dm.title
            FROM growth.decision_makers dm
            JOIN public.companies c ON c.id = dm.company_id
            """
        )
        dms = cur.fetchall()
        invalid_dm_ids: list[Any] = []
        invalid_dm_names: list[str] = []
        for dm_id, _company_id, company_name, _domain, full_name, title in dms:
            quality = is_valid_decision_maker(company_name, full_name, title)
            if not quality.valid:
                print(f"INVALID_DM {dm_id} {full_name!r}: {quality.reason}")
                invalid_dm_ids.append(dm_id)
                invalid_dm_names.append(full_name)

        cur.execute(
            """
            SELECT cc.company_contact_id, cc.company_id, c.domain, cc.value, cc.source_url
            FROM growth.company_contacts cc
            JOIN public.companies c ON c.id = cc.company_id
            WHERE lower(cc.channel) = 'email'
            """
        )
        contacts = cur.fetchall()
        invalid_contact_ids: list[Any] = []
        for contact_id, _company_id, domain, value, source_url in contacts:
            if not is_valid_company_email(domain, value, source_url):
                print(f"INVALID_COMPANY_EMAIL {contact_id} {value!r} for {domain}")
                invalid_contact_ids.append(contact_id)

        print(
            f"quality_gate invalid_decision_makers={len(invalid_dm_ids)} "
            f"invalid_company_emails={len(invalid_contact_ids)}"
        )
        if not fix:
            return 1 if invalid_dm_ids or invalid_contact_ids else 0

        if invalid_dm_ids:
            cur.execute(
                "DELETE FROM growth.decision_maker_contact_methods WHERE decision_maker_id = ANY(%s)",
                (invalid_dm_ids,),
            )
            cur.execute(
                "DELETE FROM intelligence.evidence WHERE decision_maker_id = ANY(%s)",
                (invalid_dm_ids,),
            )
            if invalid_dm_names:
                cur.execute(
                    """
                    DELETE FROM intelligence.evidence
                    WHERE claim_type = 'public_decision_maker'
                      AND claim->>'name' = ANY(%s)
                    """,
                    (invalid_dm_names,),
                )
            cur.execute(
                "DELETE FROM growth.decision_makers WHERE decision_maker_id = ANY(%s)",
                (invalid_dm_ids,),
            )

        if invalid_contact_ids:
            cur.execute(
                "DELETE FROM growth.company_contacts WHERE company_contact_id = ANY(%s)",
                (invalid_contact_ids,),
            )

        conn.commit()
        print("quality_gate cleanup committed")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(fix=args.fix))


if __name__ == "__main__":
    main()
