from __future__ import annotations

from typing import List

from .schema import ClaimContext


def validate_context(context: ClaimContext) -> List[str]:
    issues: List[str] = []

    if not context.payer:
        issues.append("payer is required")
    if not context.procedure_codes:
        issues.append("procedure_codes is required")
    if not context.denial_codes:
        issues.append("denial_codes is required")
    if not context.service_date:
        issues.append("service_date is required")

    return issues
