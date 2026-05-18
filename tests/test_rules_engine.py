import unittest

from usdent.rules.engine import build_appeal_packet, load_ruleset
from usdent.rules.schema import ClaimContext, EvidenceItem


class RulesEngineTests(unittest.TestCase):
    def test_build_packet(self) -> None:
        ruleset = load_ruleset("data/rules/delta_dental_ppo/srp.json")
        context = ClaimContext(
            payer="Delta Dental",
            patient_name="Test Patient",
            member_id="M0001",
            claim_id="C0001",
            provider_name="Dr. Test",
            service_date="2026-05-10",
            procedure_codes=["D4342"],
            denial_codes=["CO-50"],
            clinical_notes="Clinical notes here.",
            perio_chart=None,
            evidence=[
                EvidenceItem(evidence_type="PerioChart", description="Perio chart"),
            ],
        )

        packet = build_appeal_packet(ruleset, context)

        self.assertTrue(packet.rule_ids)
        self.assertIn("Radiographs", packet.missing_evidence)
        self.assertTrue(packet.narrative)


if __name__ == "__main__":
    unittest.main()
