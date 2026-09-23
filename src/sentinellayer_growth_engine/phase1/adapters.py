from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, Mapping

from .fingerprints import derive_source_record_id, raw_fingerprint
from .models import LeadSourceRecord, SourceFieldBinding


class SourceAdapter(Protocol):
    source_name: str
    adapter_version: str

    def adapt(
        self,
        payload: Mapping[str, Any],
        *,
        acquired_at: datetime,
        source_record_key: str | None = None,
        source_version: str | None = None,
    ) -> LeadSourceRecord:
        ...


class _MappedAdapter:
    source_name: str
    adapter_version: str

    field_map: dict[str, str]

    def adapt(
        self,
        payload: Mapping[str, Any],
        *,
        acquired_at: datetime,
        source_record_key: str | None = None,
        source_version: str | None = None,
    ) -> LeadSourceRecord:
        raw_payload = dict(payload)
        fp = raw_fingerprint(raw_payload)
        source_record_id = derive_source_record_id(self.source_name, source_record_key, fp)
        bindings = [
            SourceFieldBinding(
                canonical_field=canonical_field,
                source_field_name=source_field,
                raw_value=raw_payload.get(source_field),
            )
            for canonical_field, source_field in self.field_map.items()
            if source_field in raw_payload
        ]
        return LeadSourceRecord(
            source_record_id=source_record_id,
            source_name=self.source_name,
            source_version=source_version,
            source_record_key=source_record_key,
            acquired_at=acquired_at,
            source_payload=raw_payload,
            mapped_fields=bindings,
            raw_fingerprint=fp,
            adapter_version=self.adapter_version,
        )


class ScraperCityAdapter(_MappedAdapter):
    source_name = "scrapercity"
    adapter_version = "scrapercity.v1"
    field_map = {
        "display_name": "merchant_name",
        "domain": "domain",
        "canonical_url": "domain_url",
        "country_code": "country_code",
        "region": "state",
        "city": "city",
        "postal_code": "zip",
        "platform": "platform",
        "emails": "emails",
        "phones": "phones",
    }


class HunterDiscoverAdapter(_MappedAdapter):
    source_name = "hunter_discover"
    adapter_version = "hunter_discover.v1"
    field_map = {
        "display_name": "organization",
        "domain": "domain",
        "canonical_url": "website",
        "country_code": "country",
        "region": "state",
        "city": "city",
        "employee_band": "headcount",
        "company_type": "company_type",
        "year_founded": "year_founded",
        "technologies": "technologies",
        "keywords": "keywords",
        "description": "description",
    }
