from usdent.rules.engine import build_appeal_packet, load_ruleset
from usdent.rules.schema import ClaimContext, EvidenceItem


def main() -> None:
    ruleset = load_ruleset("data/rules/delta_dental_ppo/srp.json")

    context = ClaimContext(
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

    packet = build_appeal_packet(ruleset, context)

    print("Rule IDs:", packet.rule_ids)
    print("Missing evidence:", packet.missing_evidence)
    print("Narrative:\n", packet.narrative)


if __name__ == "__main__":
    main()
