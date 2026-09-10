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
        cur.execute("""SELECT (SELECT count(*) FROM public.companies), (SELECT count(DISTINCT company_id) FROM intelligence.enrichment_runs WHERE status='completed'), (SELECT count(*) FROM intelligence.evidence), (SELECT count(*) FROM growth.decision_makers), (SELECT count(*) FROM intelligence.intent_signals), (SELECT count(*) FROM intelligence.company_facts), (SELECT count(*) FROM intelligence.company_scores), (SELECT count(*) FROM growth.decision_maker_contact_methods WHERE channel='email'), (SELECT count(*) FROM growth.decision_maker_contact_methods WHERE channel='email' AND lower(coalesce(verification_status,'')) IN ('verified','deliverable','valid'))""")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("metrics query returned no row")
        keys = ["companies","enriched_companies","evidence","decision_makers","intent_signals","company_facts","scored_companies","dm_email_candidates","verified_dm_emails"]
        metrics = dict(zip(keys, row, strict=True))
        metrics["remaining_companies"] = max(metrics["companies"] - metrics["enriched_companies"], 0)

        cur.execute("""
        WITH enriched AS (SELECT DISTINCT company_id FROM intelligence.enrichment_runs WHERE status='completed'),
        ev AS (SELECT company_id,count(*) evidence,count(*) FILTER(WHERE source_url IS NOT NULL AND btrim(source_url)<>'') evidence_with_url,count(*) FILTER(WHERE confidence>=0.8) high_conf_evidence,avg(confidence) avg_evidence_conf FROM intelligence.evidence GROUP BY company_id),
        dm AS (SELECT company_id,count(*) dms FROM growth.decision_makers GROUP BY company_id),
        dm_ev AS (SELECT company_id,count(DISTINCT decision_maker_id) dm_with_evidence FROM intelligence.evidence WHERE decision_maker_id IS NOT NULL AND source_url IS NOT NULL AND btrim(source_url)<>'' GROUP BY company_id),
        intent AS (SELECT company_id,count(*) intent_signals,count(*) FILTER(WHERE evidence_id IS NOT NULL) intent_with_evidence,count(*) FILTER(WHERE signal_date IS NOT NULL) intent_dated FROM intelligence.intent_signals GROUP BY company_id),
        dm_email AS (SELECT d.company_id,count(*) FILTER(WHERE cm.channel='email') email_candidates,count(*) FILTER(WHERE cm.channel='email' AND lower(coalesce(cm.verification_status,'')) IN ('verified','deliverable','valid')) verified_emails FROM growth.decision_makers d JOIN growth.decision_maker_contact_methods cm ON cm.decision_maker_id=d.decision_maker_id GROUP BY d.company_id)
        SELECT count(*),count(*) FILTER(WHERE cf.company_id IS NOT NULL),count(*) FILTER(WHERE coalesce(ev.evidence,0)>0),count(*) FILTER(WHERE coalesce(ev.evidence,0)>=2),count(*) FILTER(WHERE coalesce(ev.evidence_with_url,0)>0),count(*) FILTER(WHERE coalesce(ev.high_conf_evidence,0)>0),count(*) FILTER(WHERE coalesce(dm.dms,0)>0),count(*) FILTER(WHERE coalesce(dm.dms,0)>=2),count(*) FILTER(WHERE coalesce(dm_ev.dm_with_evidence,0)>0),count(*) FILTER(WHERE coalesce(i.intent_signals,0)>0),count(*) FILTER(WHERE coalesce(i.intent_with_evidence,0)>0),count(*) FILTER(WHERE coalesce(i.intent_dated,0)>0),count(*) FILTER(WHERE coalesce(dm_email.email_candidates,0)>0),count(*) FILTER(WHERE coalesce(dm_email.verified_emails,0)>0),count(*) FILTER(WHERE cs.company_id IS NOT NULL),coalesce(avg(ev.avg_evidence_conf) FILTER(WHERE ev.avg_evidence_conf IS NOT NULL),0)
        FROM enriched e LEFT JOIN intelligence.company_facts cf ON cf.company_id=e.company_id LEFT JOIN ev ON ev.company_id=e.company_id LEFT JOIN dm ON dm.company_id=e.company_id LEFT JOIN dm_ev ON dm_ev.company_id=e.company_id LEFT JOIN intent i ON i.company_id=e.company_id LEFT JOIN dm_email ON dm_email.company_id=e.company_id LEFT JOIN intelligence.company_scores cs ON cs.company_id=e.company_id
        """)
        q = cur.fetchone()
        qkeys=["enriched","with_facts","with_evidence","with_2plus_evidence","evidence_url_covered","with_high_conf_evidence","with_dm","with_2plus_dm","with_dm_evidence","with_intent","intent_evidence_linked","intent_dated","with_dm_email","with_verified_dm_email","with_score","avg_evidence_conf"]
        quality=dict(zip(qkeys,q,strict=True)) if q else {}

        cur.execute("""
        WITH enriched AS (SELECT DISTINCT company_id FROM intelligence.enrichment_runs WHERE status='completed'),
        ev AS (SELECT company_id,count(*) evidence,count(*) FILTER(WHERE source_url IS NOT NULL AND btrim(source_url)<>'') evidence_with_url,avg(confidence) avg_evidence_conf FROM intelligence.evidence GROUP BY company_id),
        dm AS (SELECT company_id,count(*) dms FROM growth.decision_makers GROUP BY company_id),
        dm_ev AS (SELECT company_id,count(DISTINCT decision_maker_id) dm_with_evidence FROM intelligence.evidence WHERE decision_maker_id IS NOT NULL AND source_url IS NOT NULL AND btrim(source_url)<>'' GROUP BY company_id),
        intent AS (SELECT company_id,count(*) intent_signals,count(*) FILTER(WHERE evidence_id IS NOT NULL) intent_with_evidence,count(*) FILTER(WHERE signal_date IS NOT NULL) intent_dated FROM intelligence.intent_signals GROUP BY company_id),
        dm_email AS (SELECT d.company_id,count(*) FILTER(WHERE cm.channel='email') email_candidates,count(*) FILTER(WHERE cm.channel='email' AND lower(coalesce(cm.verification_status,'')) IN ('verified','deliverable','valid')) verified_emails FROM growth.decision_makers d JOIN growth.decision_maker_contact_methods cm ON cm.decision_maker_id=d.decision_maker_id GROUP BY d.company_id)
        SELECT c.id,c.name,c.domain,coalesce(ev.evidence,0),coalesce(ev.evidence_with_url,0),coalesce(ev.avg_evidence_conf,0),coalesce(dm.dms,0),coalesce(dm_ev.dm_with_evidence,0),coalesce(i.intent_signals,0),coalesce(i.intent_with_evidence,0),coalesce(i.intent_dated,0),coalesce(dm_email.email_candidates,0),coalesce(dm_email.verified_emails,0),(cf.company_id IS NOT NULL),(cs.company_id IS NOT NULL)
        FROM enriched e JOIN public.companies c ON c.id=e.company_id LEFT JOIN intelligence.company_facts cf ON cf.company_id=e.company_id LEFT JOIN intelligence.company_scores cs ON cs.company_id=e.company_id LEFT JOIN ev ON ev.company_id=e.company_id LEFT JOIN dm ON dm.company_id=e.company_id LEFT JOIN dm_ev ON dm_ev.company_id=e.company_id LEFT JOIN intent i ON i.company_id=e.company_id LEFT JOIN dm_email ON dm_email.company_id=e.company_id ORDER BY c.id
        """)
        quality_companies=[{"id":r[0],"name":r[1],"domain":r[2],"evidence":r[3],"evidence_with_url":r[4],"avg_evidence_conf":float(r[5] or 0),"decision_makers":r[6],"dm_with_evidence":r[7],"intent_signals":r[8],"intent_with_evidence":r[9],"intent_dated":r[10],"dm_email_candidates":r[11],"verified_dm_emails":r[12],"has_facts":bool(r[13]),"has_score":bool(r[14])} for r in cur.fetchall()]

        # Detailed company records for the interactive dashboard. Personal contact values are not
        # copied into the public Pages snapshot; contact provenance/verification state is retained.
        cur.execute("""
        WITH enriched AS (SELECT DISTINCT company_id FROM intelligence.enrichment_runs WHERE status='completed')
        SELECT c.id,c.name,c.domain,c.segment,c.country,c.city,c.source,c.revenue_est,c.visits_est,c.mx_status,c.mail_provider,c.catchall_risk,c.website,c.company_linkedin,c.notes,row_to_json(cf),row_to_json(cs)
        FROM enriched e JOIN public.companies c ON c.id=e.company_id LEFT JOIN intelligence.company_facts cf ON cf.company_id=e.company_id LEFT JOIN intelligence.company_scores cs ON cs.company_id=e.company_id ORDER BY c.name
        """)
        company_details={}
        for r in cur.fetchall():
            company_details[str(r[0])] = {"company":{"id":r[0],"name":r[1],"domain":r[2],"segment":r[3],"country":r[4],"city":r[5],"source":r[6],"revenue_est":r[7],"visits_est":r[8],"mx_status":r[9],"mail_provider":r[10],"catchall_risk":r[11],"website":r[12],"company_linkedin":r[13],"notes":r[14]},"facts":r[15],"score":r[16],"evidence":[],"decision_makers":[],"intent_signals":[],"runs":[]}
        ids=list(map(int,company_details.keys()))
        if ids:
            cur.execute("SELECT evidence_id,company_id,decision_maker_id,claim_type,claim,source_url,source_type,observed_at,event_date,confidence FROM intelligence.evidence WHERE company_id=ANY(%s) ORDER BY company_id,observed_at DESC NULLS LAST",(ids,))
            for r in cur.fetchall(): company_details[str(r[1])]["evidence"].append({"id":str(r[0]),"decision_maker_id":str(r[2]) if r[2] else None,"claim_type":r[3],"claim":r[4],"source_url":r[5],"source_type":r[6],"observed_at":r[7].isoformat() if r[7] else None,"event_date":r[8].isoformat() if r[8] else None,"confidence":float(r[9]) if r[9] is not None else None})
            cur.execute("SELECT decision_maker_id,company_id,full_name,title,role_family,role_priority,rationale,status,research_status,confidence,first_seen_at,last_verified_at FROM growth.decision_makers WHERE company_id=ANY(%s) ORDER BY company_id,role_priority NULLS LAST,full_name",(ids,))
            dm_map={}
            for r in cur.fetchall():
                item={"id":str(r[0]),"full_name":r[2],"title":r[3],"role_family":r[4],"role_priority":r[5],"rationale":r[6],"status":r[7],"research_status":r[8],"confidence":float(r[9]) if r[9] is not None else None,"first_seen_at":r[10].isoformat() if r[10] else None,"last_verified_at":r[11].isoformat() if r[11] else None,"contact_methods":[]}
                company_details[str(r[1])]["decision_makers"].append(item); dm_map[str(r[0])]=item
            if dm_map:
                cur.execute("SELECT decision_maker_id,channel,source,source_url,verification_status,verification_provider,confidence,first_seen_at,last_verified_at FROM growth.decision_maker_contact_methods WHERE decision_maker_id=ANY(%s) ORDER BY decision_maker_id,channel",(list(dm_map.keys()),))
                for r in cur.fetchall(): dm_map[str(r[0])]["contact_methods"].append({"channel":r[1],"source":r[2],"source_url":r[3],"verification_status":r[4],"verification_provider":r[5],"confidence":float(r[6]) if r[6] is not None else None,"first_seen_at":r[7].isoformat() if r[7] else None,"last_verified_at":r[8].isoformat() if r[8] else None})
            cur.execute("SELECT intent_signal_id,company_id,signal_type,signal_date,detected_at,weight,half_life_days,evidence_id,confidence,status,expires_at FROM intelligence.intent_signals WHERE company_id=ANY(%s) ORDER BY company_id,detected_at DESC",(ids,))
            for r in cur.fetchall(): company_details[str(r[1])]["intent_signals"].append({"id":str(r[0]),"signal_type":r[2],"signal_date":r[3].isoformat() if r[3] else None,"detected_at":r[4].isoformat() if r[4] else None,"weight":float(r[5]) if r[5] is not None else None,"half_life_days":r[6],"evidence_id":str(r[7]) if r[7] else None,"confidence":float(r[8]) if r[8] is not None else None,"status":r[9],"expires_at":r[10].isoformat() if r[10] else None})
            cur.execute("SELECT enrichment_run_id,company_id,run_type,provider,model_or_agent,status,started_at,completed_at,tool_usage,error_code FROM intelligence.enrichment_runs WHERE company_id=ANY(%s) ORDER BY company_id,started_at DESC",(ids,))
            for r in cur.fetchall(): company_details[str(r[1])]["runs"].append({"id":str(r[0]),"run_type":r[2],"provider":r[3],"model_or_agent":r[4],"status":r[5],"started_at":r[6].isoformat() if r[6] else None,"completed_at":r[7].isoformat() if r[7] else None,"tool_usage":r[8],"error_code":r[9]})

        cur.execute("""WITH latest AS (SELECT DISTINCT ON (er.company_id) er.company_id,er.status,er.completed_at,er.started_at FROM intelligence.enrichment_runs er ORDER BY er.company_id,er.completed_at DESC NULLS LAST,er.started_at DESC) SELECT c.id,c.name,c.domain,latest.status,latest.completed_at,latest.started_at,(SELECT count(*) FROM intelligence.evidence e WHERE e.company_id=c.id),(SELECT count(*) FROM growth.decision_makers dm WHERE dm.company_id=c.id),(SELECT count(*) FROM intelligence.intent_signals i WHERE i.company_id=c.id) FROM public.companies c JOIN latest ON latest.company_id=c.id ORDER BY COALESCE(latest.completed_at,latest.started_at) DESC NULLS LAST LIMIT 30""")
        recent_companies=[{"id":r[0],"name":r[1],"domain":r[2],"status":r[3],"completed_at":r[4].isoformat() if r[4] else None,"started_at":r[5].isoformat() if r[5] else None,"evidence":r[6],"decision_makers":r[7],"intent_signals":r[8]} for r in cur.fetchall()]
        cur.execute("SELECT er.company_id,c.name,er.provider,er.status,er.started_at,er.completed_at FROM intelligence.enrichment_runs er JOIN public.companies c ON c.id=er.company_id ORDER BY COALESCE(er.completed_at,er.started_at) DESC NULLS LAST LIMIT 30")
        recent_runs=[{"company_id":r[0],"company_name":r[1],"provider":r[2],"status":r[3],"started_at":r[4].isoformat() if r[4] else None,"completed_at":r[5].isoformat() if r[5] else None} for r in cur.fetchall()]

    OUTPUT.write_text(json.dumps({"generated_at":datetime.now(UTC).isoformat(),"metrics":metrics,"quality":quality,"quality_companies":quality_companies,"company_details":company_details,"recent_companies":recent_companies,"recent_runs":recent_runs},indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
