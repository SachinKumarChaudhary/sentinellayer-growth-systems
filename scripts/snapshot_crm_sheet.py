from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def spreadsheet_id_from_url(url: str) -> str:
    match = SHEET_ID_RE.search(url)
    if not match:
        raise ValueError("expected a Google Sheets URL containing /spreadsheets/d/<id>")
    return match.group(1)


def export_csv(url: str, *, timeout: float = 20.0) -> bytes:
    sheet_id = spreadsheet_id_from_url(url)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    params = "format=csv"
    if query.get("gid"):
        params += "&gid=" + query["gid"][0]
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?{params}"
    request = Request(
        export_url,
        headers={
            "Accept": "text/csv",
            "User-Agent": "SentinelLayer-CRM-SheetSnapshot/1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Google Sheet export failed: {exc}") from exc
    if not body.startswith(b"company,") and b"," not in body.splitlines()[0]:
        raise RuntimeError("Google Sheet export did not return CSV data")
    return body
def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot the SentinelLayer operational Google Sheet.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    try:
        body = export_csv(args.url, timeout=args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(body)
        print(f"snapshot={args.output}")
        print(f"bytes={len(body)}")
        print(f"spreadsheet_id={spreadsheet_id_from_url(args.url)}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
