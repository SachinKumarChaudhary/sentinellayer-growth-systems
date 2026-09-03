"""Platform-supported schema versions.

The registry is intentionally explicit. JSON Schema validates structure;
this registry validates compatibility policy.
"""

SUPPORTED_SCHEMA_VERSIONS = {
    "event-envelope": frozenset({"v1"}),
    "rendered-send-treatment": frozenset({"v1"}),
}


def is_supported(contract: str, version: str) -> bool:
    return version in SUPPORTED_SCHEMA_VERSIONS.get(contract, frozenset())


def require_supported(contract: str, version: str) -> None:
    if not is_supported(contract, version):
        supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS.get(contract, ()))) or "<none>"
        raise ValueError(
            f"unsupported {contract} schema version {version!r}; supported versions: {supported}"
        )
