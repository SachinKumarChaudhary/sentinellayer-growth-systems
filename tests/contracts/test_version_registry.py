"""Tests for Platform's explicit schema compatibility policy."""
from __future__ import annotations

import pytest

from .version_registry import require_supported


@pytest.mark.parametrize(
    ("contract", "version"),
    [
        ("event-envelope", "v2"),
        ("event-envelope", "v999"),
        ("rendered-send-treatment", "v2"),
        ("rendered-send-treatment", "v999"),
    ],
)
def test_unsupported_schema_versions_are_rejected(contract: str, version: str) -> None:
    with pytest.raises(ValueError, match="unsupported"):
        require_supported(contract, version)


def test_supported_v1_contracts_are_accepted() -> None:
    require_supported("event-envelope", "v1")
    require_supported("rendered-send-treatment", "v1")
