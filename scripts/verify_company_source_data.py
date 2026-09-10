#!/usr/bin/env python3
"""Reconcile growth.company_source_data against the source CSV and public.companies."""
from __future__ import annotations
import argparse, csv, os, re
from pathlib import Path
from urllib.parse import urlsplit

def norm(v):
    v=(v or '').strip().lower()
    if '://' in v: v=urlsplit(v).hostname or v
    else: v=v.split('/',1)[0]
    return v[4:] if v.startswith('www.') else v.rstrip('.')

def main():
    p=argparse.ArgumentParser(); p.add_argument('csv',type=Path); a=p.parse_args()
    with a.csv.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    csv_domains={norm(r['domain']) for r in rows}
    import psycopg
    url=os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not url: raise SystemExit('SUPABASE_DB_URL or DATABASE_URL is required')
    with psycopg.connect(url) as c, c.cursor() as q:
        q.execute("select count(*) from public.companies"); companies=q.fetchone()[0]
        q.execute("select count(*) from growth.company_source_data"); source_rows=q.fetchone()[0]
        q.execute("select normalized_domain from growth.company_source_data"); db_domains={r[0] for r in q.fetchall()}
        print({'csv_rows':len(rows),'csv_unique_domains':len(csv_domains),'public_companies':companies,'source_rows':source_rows,'missing_from_source':len(csv_domains-db_domains),'extra_in_source':len(db_domains-csv_domains)})
        if len(rows)!=1200 or len(csv_domains)!=1200 or companies!=1200 or source_rows!=1200 or csv_domains!=db_domains: raise SystemExit(1)
if __name__=='__main__': main()
