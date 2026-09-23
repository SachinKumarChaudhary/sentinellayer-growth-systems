"""Phase 1: deterministic lead intake, normalization, validation, and handoff."""

from .adapters import HunterDiscoverAdapter, ScraperCityAdapter, SourceAdapter
from .models import (
    CanonicalLead,
    DuplicateDecision,
    FieldObservation,
    LeadSourceRecord,
    Phase1Handoff,
    Phase1Result,
    ValidationFinding,
)
from .pipeline import process_source_record

__all__ = [
    "CanonicalLead",
    "DuplicateDecision",
    "FieldObservation",
    "HunterDiscoverAdapter",
    "LeadSourceRecord",
    "Phase1Handoff",
    "Phase1Result",
    "ScraperCityAdapter",
    "SourceAdapter",
    "ValidationFinding",
    "process_source_record",
]
