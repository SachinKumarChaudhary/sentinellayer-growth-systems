#!/usr/bin/env python3
"""Jina-only Lead #1 (100 Thieves) benchmark.

Uses only Jina Search and Reader. No TinyFish, Firecrawl, or browser automation.
The API key is read from JINA_API_KEY and is never printed or persisted.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

OUT = Path("jina_lead1_output")
OUT.mkdir(exist_ok=True)

COMPANY = "100 Thieves"
DOMAIN = "100thieves.com"

QUERIES = [
    '"100 Thieves" company leadership',
    '"100 Thieves" "Julie Van"',
    '"100 Thieves" "Selina Garcia"',
    '"100 Thieves" security technology',
    '"100 Thieves" account login Shopify',
    '"100 Thieves" fraud cybersecurity',
    '"100 Thieves" 2026 leadership',
    'site:linkedin.com/in "100 Thieves" leadership',
]

EXPECTED = {
    "Julie Van": "current COO",
    "Selina Garcia": "current Director of IT & Infrastructure",
    "Matthew Haag": "Founder & CEO",
    "Jacob Toft-Andersen": "President",
}


def jina_get(url: str) -> tuple[int, str, dict[str, str]]:
    key = os.environ.get("JINA_API_KEY", "")
    if not key:
        raise RuntimeError("JINA_API_KEY is not configured")
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "SentinelLayer-Jina-Benchmark/1.0",
        },
    )
    with urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body, dict(resp.headers)


def search(q: str) -> dict:
    url = "https://s.jina.ai/?q=" + quote(q, safe="")
    started = time.time()
    try:
        status, body, headers = jina_get(url)
        return {
            "query": q,
            "status": status,
            "latency_seconds": round(time.time() - started, 3),
            "body": body,
            "content_type": headers.get("content-type", ""),
        }
    except Exception as exc:
        return {
            "query": q,
            "status": None,
            "latency_seconds": round(time.time() - started, 3),
            "error": type(exc).__name__ + ": " + str(exc),
        }


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r'https?://[^\s<>\"\']+', text)
    clean: list[str] = []
    for u in urls:
        u = u.rstrip(".,);]")
        if u not in clean:
            clean.append(u)
    return clean


def relevant_urls(search_results: list[dict]) -> list[str]:
    urls: list[str] = []
    for result in search_results:
        for u in extract_urls(result.get("body", "")):
            host = urlparse(u).netloc.lower()
            if any(x in host for x in ("100thieves.com", "linkedin.com", "forbes.com", "thinkla.com")):
                if u not in urls:
                    urls.append(u)
    return urls[:20]


def read(url: str) -> dict:
    reader_url = "https://r.jina.ai/" + url
    started = time.time()
    try:
        status, body, headers = jina_get(reader_url)
        return {
            "url": url,
            "status": status,
            "latency_seconds": round(time.time() - started, 3),
            "content_type": headers.get("content-type", ""),
            "body": body,
        }
    except Exception as exc:
        return {
            "url": url,
            "status": None,
            "latency_seconds": round(time.time() - started, 3),
            "error": type(exc).__name__ + ": " + str(exc),
        }


def evidence_flags(text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        "company_mentioned": "100 thieves" in low or "100thieves" in low,
        "julie_van": "julie van" in low,
        "selina_garcia": "selina garcia" in low,
        "matthew_haag": "matthew haag" in low or "nadeshot" in low,
        "jacob_toft": "jacob toft-andersen" in low or "jacob toft andersen" in low,
        "coo": "chief operating officer" in low or " coo" in low,
        "it_infrastructure": "it & infrastructure" in low or "it and infrastructure" in low,
        "founder_ceo": "founder & ceo" in low or "founder and ceo" in low,
        "president": "president" in low,
        "login_account": "account" in low and ("sign in" in low or "login" in low or "log in" in low),
        "shopify": "shopify" in low,
        "security": "security" in low or "cybersecurity" in low,
    }


def main() -> None:
    started = time.time()
    searches = [search(q) for q in QUERIES]
    (OUT / "search_results.json").write_text(json.dumps(searches, indent=2), encoding="utf-8")

    urls = relevant_urls(searches)
    # Always test the two known first-party pages because they are central to ICP/session evidence.
    for u in [
        "https://100thieves.com/pages/privacy-policy",
        "https://100thieves.com/pages/terms-of-service",
    ]:
        if u not in urls:
            urls.append(u)

    reads = [read(u) for u in urls[:20]]
    (OUT / "reader_results.json").write_text(json.dumps(reads, indent=2), encoding="utf-8")

    combined = "\n\n".join(r.get("body", "") for r in reads)
    flags = evidence_flags(combined)

    found_people = {name: name.lower() in combined.lower() for name in EXPECTED}
    report = {
        "experiment": "Jina Search + Jina Reader only",
        "lead": {"company": COMPANY, "domain": DOMAIN, "company_id": 96},
        "constraints": {
            "tinyfish": False,
            "firecrawl": False,
            "browser_automation": False,
            "jina_search_queries": len(QUERIES),
            "jina_reader_urls": len(reads),
        },
        "candidate_name_recall": found_people,
        "evidence_flags": flags,
        "url_count": len(urls),
        "successful_searches": sum(1 for x in searches if x.get("status") == 200),
        "successful_reads": sum(1 for x in reads if x.get("status") == 200),
        "total_latency_seconds": round(time.time() - started, 3),
        "ground_truth_for_manual_review": EXPECTED,
        "note": "This is a retrieval benchmark. Final identity/currentness/campaign decisions must remain SentinelLayer validator decisions.",
    }
    (OUT / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    markdown = [
        "# Jina-only Lead #1 benchmark",
        "",
        f"**Company:** {COMPANY}  ",
        f"**Domain:** {DOMAIN}  ",
        "**Provider:** Jina Search + Jina Reader only",
        "",
        "## Retrieval",
        f"- Search queries: {len(QUERIES)}",
        f"- Candidate URLs: {len(urls)}",
        f"- Successful searches: {report['successful_searches']}/{len(searches)}",
        f"- Successful reads: {report['successful_reads']}/{len(reads)}",
        f"- Total wall time: {report['total_latency_seconds']}s",
        "",
        "## Candidate name recall",
    ]
    for name, found in found_people.items():
        markdown.append(f"- {name}: {'FOUND' if found else 'NOT FOUND'}")
    markdown += ["", "## Evidence flags"]
    for k, v in flags.items():
        markdown.append(f"- {k}: {'YES' if v else 'NO'}")
    markdown += [
        "",
        "## Ground truth for manual comparison",
    ]
    for name, role in EXPECTED.items():
        markdown.append(f"- {name}: {role}")
    markdown += [
        "",
        "## Important",
        "This report intentionally does not assign identity verification, confidence, FIT, INTENT, or campaign readiness. Those are SentinelLayer decisions over collected evidence.",
    ]
    (OUT / "quality_report.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print("Jina Lead #1 experiment complete")
    print(f"searches={len(searches)} successful={report['successful_searches']}")
    print(f"reads={len(reads)} successful={report['successful_reads']}")
    print(f"wall_time_seconds={report['total_latency_seconds']}")


if __name__ == "__main__":
    main()
