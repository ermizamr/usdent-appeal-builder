from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvidenceItem:
    evidence_type: str
    description: str
    filename: Optional[str] = None


@dataclass
class ClaimContext:
    payer: str
    patient_name: str
    member_id: str
    claim_id: str
    provider_name: str
    service_date: str
    procedure_codes: List[str]
    denial_codes: List[str]
    clinical_notes: str
    perio_chart: Optional[Dict[str, str]] = None
    evidence: List[EvidenceItem] = field(default_factory=list)


@dataclass
class DenialRule:
    rule_id: str
    payer: str
    procedure_codes: List[str]
    denial_codes: List[str]
    required_evidence_types: List[str]
    narrative_template: str


@dataclass
class RuleSet:
    version: str
    payer: str
    rules: List[DenialRule]


@dataclass
class AppealPacket:
    rule_ids: List[str]
    narrative: str
    missing_evidence: List[str]
    evidence_checklist: List[str]
    notes: str
