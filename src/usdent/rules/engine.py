from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .narrative import render_narrative
from .schema import AppealPacket, ClaimContext, DenialRule, EvidenceItem, RuleSet


def load_ruleset(path: str | Path) -> RuleSet:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    ruleset_payer = raw.get("payer", "MULTI")
    rules = [
        DenialRule(
            rule_id=item["id"],
            payer=item.get("payer", ruleset_payer),
            procedure_codes=item["procedure_codes"],
            denial_codes=item["denial_codes"],
            required_evidence_types=item["required_evidence_types"],
            narrative_template=item["narrative_template"],
        )
        for item in raw["rules"]
    ]
    return RuleSet(version=raw["version"], payer=ruleset_payer, rules=rules)


def _normalize_codes(codes: List[str]) -> List[str]:
    return [code.strip().upper() for code in codes]


def match_rules(ruleset: RuleSet, context: ClaimContext) -> List[DenialRule]:
    context_proc = set(_normalize_codes(context.procedure_codes))
    context_denial = set(_normalize_codes(context.denial_codes))
    matches: List[DenialRule] = []

    for rule in ruleset.rules:
        if rule.payer.lower() != context.payer.lower():
            continue
        if not context_proc.intersection(_normalize_codes(rule.procedure_codes)):
            continue
        rule_denial = _normalize_codes(rule.denial_codes)
        if rule_denial and "*" not in rule_denial and not context_denial.intersection(rule_denial):
            continue
        matches.append(rule)

    return matches


def _missing_evidence(required: List[str], evidence: List[EvidenceItem]) -> List[str]:
    provided = {item.evidence_type.lower() for item in evidence}
    return [item for item in required if item.lower() not in provided]


def build_appeal_packet(ruleset: RuleSet, context: ClaimContext) -> AppealPacket:
    matches = match_rules(ruleset, context)

    if not matches:
        return AppealPacket(
            rule_ids=[],
            narrative="",
            missing_evidence=[],
            evidence_checklist=[],
            notes="No matching rule found for payer/procedure/denial codes.",
        )

    narratives = [render_narrative(rule, context) for rule in matches]
    required_evidence = []
    for rule in matches:
        required_evidence.extend(rule.required_evidence_types)

    missing = _missing_evidence(required_evidence, context.evidence)

    return AppealPacket(
        rule_ids=[rule.rule_id for rule in matches],
        narrative="\n\n".join(narratives),
        missing_evidence=missing,
        evidence_checklist=required_evidence,
        notes="",
    )
