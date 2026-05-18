from .schema import ClaimContext, EvidenceItem


def build_sample_context() -> ClaimContext:
    return ClaimContext(
        payer="Delta Dental",
        patient_name="Alex Patient",
        member_id="M123456",
        claim_id="C987654",
        provider_name="Dr. Sample",
        service_date="2026-05-01",
        procedure_codes=["D4342"],
        denial_codes=["CO-50"],
        clinical_notes="Generalized periodontal therapy indicated based on findings.",
        perio_chart={"3": "6mm", "4": "5mm", "5": "6mm"},
        evidence=[
            EvidenceItem(
                evidence_type="PerioChart",
                description="Perio chart dated 2026-05-01",
            ),
            EvidenceItem(
                evidence_type="ClinicalNotes",
                description="SOAP note",
            ),
        ],
    )
