from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ParsedStatus:
    raw: str | None
    category: str
    confidence: str
    actionable_due_at: datetime | None
    requires_review: bool


@dataclass(frozen=True)
class SourceSnapshot:
    source_name: str
    source_path: str
    captured_at: str
    file_sha256: str
    row_count: int
    headers: list[str]
    null_rates: dict[str, float]
    sample_row_hashes: list[str]
    importer_version: str
def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_hash(row: dict[str, Any]) -> str:
    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def normalize_domain(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    raw = value.strip().lower()
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def normalize_linkedin(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    parsed = urlsplit(value.strip() if "://" in value else f"https://{value.strip()}")
    host = (parsed.hostname or "").lower().strip(".")
    if not (host == "linkedin.com" or host.endswith(".linkedin.com")):
        return None
    path = parsed.path.rstrip("/")
    return f"https://www.linkedin.com{path}" if path else None
def normalize_email(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    email = value.strip().lower()
    local, sep, domain = email.partition("@")
    if not sep or not local or "." not in domain or " " in email:
        return None
    return email


def normalize_phone(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    raw = value.strip()
    if re.fullmatch(r"[+\-]?\d+(?:\.\d+)?[eE][+\-]?\d+", raw):
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits if 7 <= len(digits) <= 15 else None
def parse_lead_status(raw: str | None) -> ParsedStatus:
    if raw is None or not raw.strip():
        return ParsedStatus(raw, "UNKNOWN", "high", None, True)
    text = raw.strip()
    lower = text.lower()
    if "demo session booked" in lower or "demo booked" in lower:
        return ParsedStatus(text, "DEMO_BOOKED", "high", None, True)
    if "not qualified" in lower:
        return ParsedStatus(text, "NOT_QUALIFIED", "high", None, False)
    if "no response" in lower:
        return ParsedStatus(text, "NO_RESPONSE", "high", None, False)
    if "email sent" in lower or "message sent" in lower:
        return ParsedStatus(text, "OUTREACH_SENT", "high", None, False)
    return ParsedStatus(text, "UNMAPPED", "low", None, True)
def _read_rows(path: Path, limit: int = 0) -> tuple[list[str], list[dict[str, Any]]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            rows: list[dict[str, Any]] = []
            for row in reader:
                rows.append(dict(row))
                if limit and len(rows) >= limit:
                    break
            return headers, rows
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("rows", [])
        if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
            raise ValueError("JSON source must contain a list of objects or {rows:[...]}")
        rows = rows[:limit] if limit else rows
        headers = sorted({key for row in rows for key in row})
        return headers, rows
    raise ValueError(f"unsupported source type: {path.suffix}")
def load_source_rows(path: Path, *, limit: int = 0) -> tuple[list[str], list[dict[str, Any]]]:
    return _read_rows(path, limit=limit)


def profile_source(
    *, source_name: str, path: Path, importer_version: str = "crm-mvp.v1", limit: int = 0
) -> SourceSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    headers, rows = _read_rows(path, limit=limit)
    counts = {header: 0 for header in headers}
    for row in rows:
        for header in headers:
            value = row.get(header)
            if value is None or (isinstance(value, str) and not value.strip()):
                counts[header] += 1
    denominator = len(rows) or 1
    return SourceSnapshot(
        source_name=source_name,
        source_path=str(path),
        captured_at=datetime.now().astimezone().isoformat(),
        file_sha256=_sha256_path(path),
        row_count=len(rows),
        headers=headers,
        null_rates={key: counts[key] / denominator for key in headers},
        sample_row_hashes=[row_hash(row) for row in rows[:10]],
        importer_version=importer_version,
    )
@dataclass(frozen=True)
class StagedRow:
    source_name: str
    source_snapshot_hash: str
    source_row_number: int
    source_row_hash: str
    raw_row: dict[str, Any]
    parser_result: dict[str, Any]
    disposition: str
    importer_version: str


def classify_row(row: dict[str, Any]) -> ParsedStatus:
    raw = row.get("lead_status") or row.get("Lead Status") or row.get("status")
    return parse_lead_status(str(raw) if raw is not None else None)
def stage_row_payload(staged: StagedRow) -> dict[str, Any]:
    if staged.disposition not in {"imported", "updated", "merged", "quarantined", "rejected"}:
        raise ValueError("invalid migration disposition")
    return {
        "source_name": staged.source_name,
        "source_snapshot_hash": staged.source_snapshot_hash,
        "source_row_number": staged.source_row_number,
        "source_row_hash": staged.source_row_hash,
        "raw_row": staged.raw_row,
        "parser_result": staged.parser_result,
        "disposition": staged.disposition,
        "importer_version": staged.importer_version,
    }


def reconciliation_is_complete(
    *, source_rows: int, imported: int, updated: int, merged: int,
    quarantined: int, rejected: int,
) -> bool:
    return source_rows == imported + updated + merged + quarantined + rejected
def build_staged_rows(
    *, source_name: str, snapshot_hash: str, rows: list[dict[str, Any]],
    importer_version: str = "crm-mvp.v1",
) -> list[StagedRow]:
    staged: list[StagedRow] = []
    for number, row in enumerate(rows, start=1):
        parsed = classify_row(row)
        disposition = "quarantined" if parsed.requires_review else "imported"
        staged.append(
            StagedRow(
                source_name=source_name,
                source_snapshot_hash=snapshot_hash,
                source_row_number=number,
                source_row_hash=row_hash(row),
                raw_row=dict(row),
                parser_result=asdict(parsed),
                disposition=disposition,
                importer_version=importer_version,
            )
        )
    return staged
def persist_staged_row(connection_factory: Callable[[], Any], staged: StagedRow) -> dict[str, Any]:
    payload = stage_row_payload(staged)
    with connection_factory() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into crm.migration_rows(
              source_name, source_snapshot_hash, source_row_number,
              source_row_hash, raw_row, parser_result, disposition, importer_version
            ) values (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
            on conflict (source_name, source_snapshot_hash, source_row_number)
            do nothing
            returning migration_row_id, disposition, created_at
            """,
            (
                payload["source_name"], payload["source_snapshot_hash"],
                payload["source_row_number"], payload["source_row_hash"],
                json.dumps(payload["raw_row"], ensure_ascii=False),
                json.dumps(payload["parser_result"], default=str),
                payload["disposition"], payload["importer_version"],
            ),
        )
        row = cur.fetchone()
        if row is not None:
            return dict(row)
        cur.execute(
            """
            select migration_row_id, disposition, created_at
            from crm.migration_rows
            where source_name=%s and source_snapshot_hash=%s and source_row_number=%s
            """,
            (payload["source_name"], payload["source_snapshot_hash"], payload["source_row_number"]),
        )
        existing = cur.fetchone()
        if existing is None:
            raise RuntimeError("staged migration row disappeared after conflict")
        return dict(existing)

OPERATIONAL_SHEET_HEADERS = [
    "company", "buyer", "title", "linkedin_url",
    "Phone ", "Email", "Lead Status", "Intent",
]


@dataclass(frozen=True)
class OperationalSheetRow:
    source_row_number: int
    company: str | None
    buyer: str | None
    title: str | None
    linkedin_url: str | None
    emails: list[str]
    phones: list[str]
    raw_status: str | None
    status_category: str
    raw_intent: str | None
    invalid_contact_values: list[str]
    structural_row: bool
    duplicate_linkedin_row: int | None

def _split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r";|\n", value) if part.strip()]


def _split_email_values(value: str | None) -> list[str]:
    if not value:
        return []
    matches = re.findall(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value)
    return matches or _split_multi_value(value)


def parse_operational_sheet_row(
    row: dict[str, Any], *, source_row_number: int
) -> OperationalSheetRow:
    company = (row.get("company") or "").strip() or None
    buyer = (row.get("buyer") or "").strip() or None
    title = (row.get("title") or "").strip() or None
    raw_linkedin = (row.get("linkedin_url") or "").strip() or None
    raw_emails = _split_email_values(row.get("Email"))
    raw_phones = _split_multi_value(row.get("Phone "))
    emails = [value for value in (normalize_email(x) for x in raw_emails) if value]
    phones = [value for value in (normalize_phone(x) for x in raw_phones) if value]
    invalid = []
    invalid.extend(x for x in raw_emails if normalize_email(x) is None)
    invalid.extend(x for x in raw_phones if normalize_phone(x) is None)
    linkedin = normalize_linkedin(raw_linkedin)
    if raw_linkedin and linkedin is None:
        invalid.append(raw_linkedin)
    raw_status = (row.get("Lead Status") or "").strip() or None
    raw_intent = (row.get("Intent") or "").strip() or None
    status = parse_lead_status(raw_status)
    structural = not company or (
        company is not None
        and not any([buyer, title, raw_linkedin, raw_emails, raw_phones, raw_status, raw_intent])
    )
    return OperationalSheetRow(
        source_row_number=source_row_number,
        company=company,
        buyer=buyer,
        title=title,
        linkedin_url=linkedin,
        emails=emails,
        phones=phones,
        raw_status=raw_status,
        status_category=status.category,
        raw_intent=raw_intent,
        invalid_contact_values=invalid,
        structural_row=structural,
        duplicate_linkedin_row=None,
    )

def build_operational_sheet_staged_rows(
    *, source_name: str, snapshot_hash: str,
    rows: list[dict[str, Any]], importer_version: str = "crm-mvp.sheet.v1",
) -> list[StagedRow]:
    first_linkedin_row: dict[str, int] = {}
    staged: list[StagedRow] = []
    for number, row in enumerate(rows, start=1):
        parsed = parse_operational_sheet_row(row, source_row_number=number)
        parser_result = asdict(parsed)
        if parsed.structural_row:
            disposition = "rejected"
            parser_result["reason"] = "non_lead_structural_row"
        elif parsed.duplicate_linkedin_row is not None:
            disposition = "merged"
        elif parsed.invalid_contact_values:
            disposition = "quarantined"
            parser_result["reason"] = "invalid_contact_identity_value"
        elif parsed.linkedin_url and parsed.linkedin_url in first_linkedin_row:
            disposition = "merged"
            parser_result["duplicate_linkedin_row"] = first_linkedin_row[parsed.linkedin_url]
        else:
            disposition = "imported"
        if parsed.linkedin_url and parsed.linkedin_url not in first_linkedin_row:
            first_linkedin_row[parsed.linkedin_url] = number
        staged.append(
            StagedRow(
                source_name=source_name,
                source_snapshot_hash=snapshot_hash,
                source_row_number=number,
                source_row_hash=row_hash(row),
                raw_row=dict(row),
                parser_result=parser_result,
                disposition=disposition,
                importer_version=importer_version,
            )
        )
    return staged
def operational_sheet_profile(staged_rows: list[StagedRow]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    intent_count = 0
    duplicate_linkedin_rows = 0
    invalid_rows = 0
    structural_rows = 0
    for item in staged_rows:
        counts[item.disposition] = counts.get(item.disposition, 0) + 1
        parsed = item.parser_result
        category = parsed.get("status_category")
        if category:
            status_counts[category] = status_counts.get(category, 0) + 1
        if parsed.get("raw_intent"):
            intent_count += 1
        if parsed.get("duplicate_linkedin_row"):
            duplicate_linkedin_rows += 1
        if parsed.get("invalid_contact_values"):
            invalid_rows += 1
        if parsed.get("structural_row"):
            structural_rows += 1
    return {
        "source_rows": len(staged_rows),
        "dispositions": counts,
        "status_categories": status_counts,
        "intent_rows": intent_count,
        "duplicate_linkedin_rows": duplicate_linkedin_rows,
        "invalid_identity_rows": invalid_rows,
        "structural_rows": structural_rows,
        "reconciliation_complete": sum(counts.values()) == len(staged_rows),
    }
