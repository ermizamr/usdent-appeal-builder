from usdent.rules.engine import build_appeal_packet, load_ruleset
from usdent.rules.sample_context import build_sample_context
from usdent.rules.validation import validate_context


def main() -> None:
    ruleset = load_ruleset("data/rules/delta_dental_ppo/srp.json")
    context = build_sample_context()

    issues = validate_context(context)
    if issues:
        print("Context issues:", issues)
        return

    packet = build_appeal_packet(ruleset, context)
    print("Rule IDs:", packet.rule_ids)
    print("Missing evidence:", packet.missing_evidence)
    print("Narrative:\n", packet.narrative)


if __name__ == "__main__":
    main()
