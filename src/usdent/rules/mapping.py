from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class AdaFormField:
    field_id: str
    value: str


@dataclass
class AdaFormMapping:
    form_version: str
    fields: List[AdaFormField]


def build_ada_form_mapping(claim_id: str, member_id: str, provider_name: str) -> AdaFormMapping:
    # Placeholder mapping for initial wiring. Replace with full ADA form definitions.
    fields = [
        AdaFormField(field_id="claim_id", value=claim_id),
        AdaFormField(field_id="member_id", value=member_id),
        AdaFormField(field_id="provider_name", value=provider_name),
    ]
    return AdaFormMapping(form_version="2025", fields=fields)
