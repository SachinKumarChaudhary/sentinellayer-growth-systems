#!/usr/bin/env python3
"""Bounded preflight for Phase 2 Indian corporate-data providers.

This checks connectivity and response shape only. It does not write to the
database, process leads, or make an entity-resolution decision.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA_GOV_RESOURCE_ID = "4dbe5667-7b6b-41d7-82af-211562424d9a"
DATA_GOV_BASE_URL = "https://api.data.gov.in/resource"
QORPIQ_STATUS_URL = "https://mcp.qorpiq.com/v1/status"
TIMEOUT_SECONDS = 20


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def check_data_gov() -> bool:
    api_key = os.environ.get("DATA_GOV_IN_API_KEY")
    if not api_key:
        print("data_gov_in=missing_key")
        return False

    query = urlencode(
        {
            "api-key": api_key,
            "format": "json",
            "limit": "1",
        }
    )
    request = Request(
        f"{DATA_GOV_BASE_URL}/{DATA_GOV_RESOURCE_ID}?{query}",
        headers={"User-Agent": "SentinelLayer-Phase2-provider-preflight/1.0"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if response.status != 200:
                print(f"data_gov_in=http_{response.status}")
                return False
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"data_gov_in=failed ({type(exc).__name__})")
        return False

    records = payload.get("records")
    if not isinstance(records, list) or not records:
        print("data_gov_in=invalid_or_empty_records")
        return False

    total = payload.get("total")
    print(f"data_gov_in=ok http=200 sample_records={len(records)} total={total}")
    return True


def check_qorpiq_status() -> bool:
    request = Request(
        QORPIQ_STATUS_URL,
        headers={"Accept": "application/json", "User-Agent": "SentinelLayer-Phase2-provider-preflight/1.0"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if response.status != 200:
                print(f"qorpiq_status=http_{response.status}")
                return False
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"qorpiq_status=failed ({type(exc).__name__})")
        return False

    overall = payload.get("overall") or {}
    company = next(
        (item for item in payload.get("components", []) if item.get("key") == "company"),
        {},
    )
    director = next(
        (item for item in payload.get("components", []) if item.get("key") == "director"),
        {},
    )
    state = overall.get("state")
    print(
        "qorpiq_status="
        f"{state} company={company.get('state', 'unknown')} "
        f"director={director.get('state', 'unknown')}"
    )
    return state == "up" and company.get("state") == "up"


def main() -> int:
    data_gov_ok = check_data_gov()
    qorpiq_ok = check_qorpiq_status()

    if not data_gov_ok or not qorpiq_ok:
        return fail("one or more Indian registry provider preflight checks failed")

    print("registry_provider_preflight=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
