from __future__ import annotations

import re
from urllib.parse import urlparse

_COMPANY_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    tokens = [token for token in _NON_ALNUM.split(value.lower()) if token]
    tokens = [token for token in tokens if token not in _COMPANY_SUFFIXES]
    return " ".join(tokens)


def name_tokens(value: str | None) -> frozenset[str]:
    normalized = normalize_name(value)
    return frozenset(normalized.split())


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    candidate = value.strip().lower()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").rstrip(".")
    return host.removeprefix("www.")


_COMMON_TWO_LEVEL_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "com.mx",
    "co.in",
    "co.jp",
    "com.sg",
    "com.hk",
}


def registrable_domain(value: str | None) -> str:
    host = normalize_domain(value)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host

    suffix = ".".join(parts[-2:])
    if suffix in _COMMON_TWO_LEVEL_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return suffix


def geography_tokens(values: list[str] | tuple[str, ...]) -> frozenset[str]:
    return frozenset(normalize_name(value) for value in values if normalize_name(value))
