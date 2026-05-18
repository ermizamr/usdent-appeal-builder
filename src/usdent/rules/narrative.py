from __future__ import annotations

from string import Formatter
from typing import Dict

from .schema import ClaimContext, DenialRule


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _summarize_perio_chart(perio_chart: Dict[str, str] | None) -> str:
    if not perio_chart:
        return ""
    parts = [f"{tooth}:{depth}" for tooth, depth in perio_chart.items()]
    return "; ".join(parts)


def _build_template_context(context: ClaimContext) -> Dict[str, str]:
    return {
        "payer": context.payer,
        "patient_name": context.patient_name,
        "member_id": context.member_id,
        "claim_id": context.claim_id,
        "provider_name": context.provider_name,
        "service_date": context.service_date,
        "procedure_codes": ", ".join(context.procedure_codes),
        "denial_codes": ", ".join(context.denial_codes),
        "clinical_notes": context.clinical_notes,
        "perio_chart_summary": _summarize_perio_chart(context.perio_chart),
    }


def render_narrative(rule: DenialRule, context: ClaimContext) -> str:
    template_context = _build_template_context(context)
    return Formatter().vformat(rule.narrative_template, (), _SafeDict(template_context))
