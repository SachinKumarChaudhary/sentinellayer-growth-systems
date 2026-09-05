"""Machine-readable compatibility tests for Platform-owned schema versions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads(
    (ROOT / "schemas" / "contract-version-registry.json").read_text(encoding="utf-8")
)


def supported(contract: str, version: str) -> bool:
    return version in REGISTRY["supported"].get(contract, [])


@pytest.mark.parametrize(
    ("contract", "version"),
    [
        ("event-envelope", "v2"),
        ("event-envelope", "v999"),
        ("rendered-send-treatment", "v2"),
        ("rendered-send-treatment", "v999"),
    ],
)
def test_unsupported_versions_are_rejected_by_registry(
    contract: str, version: str
) -> None:
    assert not supported(contract, version)


def test_registered_v1_contracts_are_supported() -> None:
    assert supported("event-envelope", "v1")
    assert supported("rendered-send-treatment", "v1")
