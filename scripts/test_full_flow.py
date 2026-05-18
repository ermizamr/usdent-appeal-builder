import argparse
from pathlib import Path

from usdent.automation import (
    EobData,
    build_appeal_text,
    extract_eob_data,
    fill_ada_form,
    generate_narrative,
)


def _coalesce_payer(eob_data: EobData, payer_override: str | None) -> EobData:
    if payer_override and not eob_data.payer_name:
        eob_data.payer_name = payer_override
    return eob_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full EOB -> appeal flow.")
    parser.add_argument("eob_path", help="Path to EOB PDF, image, or TXT")
    parser.add_argument("--ada-template", help="Path to ADA 2019/2024 blank form PDF")
    parser.add_argument("--output-pdf", help="Path to output appeal PDF")
    parser.add_argument("--output-text", help="Path to output appeal text file")
    parser.add_argument("--payer", help="Override payer name if not found")
    parser.add_argument("--use-ai", action="store_true", help="Use AI narrative generation")
    args = parser.parse_args()

    eob_path = Path(args.eob_path)
    if not eob_path.exists():
        raise FileNotFoundError(f"EOB file not found: {eob_path}")

    eob_data = extract_eob_data(str(eob_path))
    eob_data = _coalesce_payer(eob_data, args.payer)
    narrative = generate_narrative(eob_data, use_ai=args.use_ai)

    if args.output_text:
        text = build_appeal_text(eob_data, narrative)
        Path(args.output_text).write_text(text, encoding="utf-8")
    elif args.ada_template and args.output_pdf:
        fill_ada_form(
            eob_data,
            narrative,
            template_path=args.ada_template,
            output_path=args.output_pdf,
        )
    else:
        raise ValueError("Provide either --output-text or both --ada-template and --output-pdf")

    print("Extracted:")
    print("  Patient:", eob_data.patient_name)
    print("  Payer:", eob_data.payer_name)
    print("  DOS:", eob_data.date_of_service)
    print("  Claim ID:", eob_data.claim_id)
    print("  Procedure Code:", eob_data.procedure_code)
    print("  Denial Code:", eob_data.denial_code)
    print("  Denial Reason:", eob_data.denial_reason)
    print("  Amount Billed:", eob_data.amount_billed)
    print("  Amount Denied:", eob_data.amount_denied)
    print("Narrative:")
    print(narrative)
    if args.output_text:
        print("Output Text:", args.output_text)
    if args.output_pdf:
        print("Output PDF:", args.output_pdf)


if __name__ == "__main__":
    main()
