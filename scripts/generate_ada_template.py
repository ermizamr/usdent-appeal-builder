"""Generate a fillable ADA-style dental claim form template.

This builds a faithful ADA Dental Claim Form *facsimile* (not the copyrighted
official ADA form) as a one-page PDF with named AcroForm text fields. The layout
mirrors the real ADA Dental Claim Form sections and box numbers so that a
licensed official ADA PDF can be swapped in via ``USDENT_ADA_TEMPLATE`` with the
same field mapping. The field names match the ``pdf_field`` entries in
``data/ada_form_mapping.json`` so ``usdent.automation.fill_ada_form`` can populate
them with pypdf.

Run once to (re)generate the committed template:

    python scripts/generate_ada_template.py

Requires reportlab: pip install reportlab
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover - dev-only dependency
    raise SystemExit("reportlab is required. Install with pip install reportlab.") from exc


ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "data" / "ada_form_mapping.json"
OUTPUT_PATH = ROOT / "data" / "ada_claim_template.pdf"

PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 0.4 * inch
LEFT = MARGIN
RIGHT = PAGE_WIDTH - MARGIN
USABLE = RIGHT - LEFT

# Box numbers that the automation fills. Everything else is drawn as an empty
# box for visual fidelity with the real ADA form.
FILLABLE = {
    "Box1", "Box2", "Box3", "Box20", "Box24", "Box29", "Box31",
    "Box35", "Box48", "Box49", "Box50", "Box52", "Box53", "Box54",
}


def _expected_fields() -> set[str]:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return {f["pdf_field"] for f in mapping.get("fields", []) if f.get("pdf_field")}


class FormBuilder:
    """Small helper around a reportlab canvas to draw labeled ADA cells."""

    def __init__(self, pdf: canvas.Canvas) -> None:
        self.pdf = pdf
        self.form = pdf.acroForm
        self.fields_drawn: set[str] = set()

    def section(self, x: float, top: float, w: float, title: str) -> float:
        """Draw a shaded section header bar. Returns the y below it."""
        h = 14
        self.pdf.setFillGray(0.85)
        self.pdf.rect(x, top - h, w, h, stroke=1, fill=1)
        self.pdf.setFillGray(0.0)
        self.pdf.setFont("Helvetica-Bold", 7.5)
        self.pdf.drawString(x + 3, top - h + 4, title.upper())
        return top - h

    def cell(
        self,
        x: float,
        top: float,
        w: float,
        h: float,
        num: str,
        label: str,
        field: str | None = None,
        multiline: bool = False,
        font_size: int = 9,
    ) -> None:
        """Draw a bordered cell with a box number + label, optionally fillable."""
        pdf = self.pdf
        pdf.setLineWidth(0.5)
        pdf.rect(x, top - h, w, h, stroke=1, fill=0)

        pdf.setFont("Helvetica", 5.5)
        pdf.setFillGray(0.3)
        caption = f"{num}. {label}" if num else label
        pdf.drawString(x + 2, top - 7, caption[:90])
        pdf.setFillGray(0.0)

        if field:
            pad = 2
            fy = top - h + pad
            fh = h - 9 - pad if not multiline else h - 9 - pad
            self.form.textfield(
                name=field,
                tooltip=label,
                x=x + pad,
                y=fy,
                width=w - 2 * pad,
                height=max(fh, 9),
                fontName="Helvetica",
                fontSize=font_size,
                borderWidth=0,
                forceBorder=False,
                fieldFlags="multiline" if multiline else "",
            )
            self.fields_drawn.add(field)


def _draw_header(pdf: canvas.Canvas) -> float:
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(LEFT, PAGE_HEIGHT - 0.55 * inch, "Dental Claim Form")
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillGray(0.35)
    pdf.drawRightString(
        RIGHT,
        PAGE_HEIGHT - 0.5 * inch,
        "ADA-style facsimile — not the copyrighted official ADA Dental Claim Form",
    )
    pdf.drawRightString(
        RIGHT,
        PAGE_HEIGHT - 0.62 * inch,
        "For a licensed official form, set USDENT_ADA_TEMPLATE",
    )
    pdf.setFillGray(0.0)
    return PAGE_HEIGHT - 0.8 * inch


def main() -> None:
    expected = _expected_fields()
    if not expected:
        raise SystemExit(f"No fields found in {MAPPING_PATH}")

    pdf = canvas.Canvas(str(OUTPUT_PATH), pagesize=letter)
    b = FormBuilder(pdf)

    y = _draw_header(pdf)

    # --- Header of Transaction band ---------------------------------------
    y = b.section(LEFT, y, USABLE, "Header Information")
    row_h = 30
    b.cell(LEFT, y, USABLE * 0.6, row_h, "1", "Type of Transaction", "Box1")
    b.cell(LEFT + USABLE * 0.6, y, USABLE * 0.4, row_h, "2",
           "Predetermination / Original Claim Number", "Box2")
    y -= row_h + 4

    # --- Insurance Company / Dental Benefit Plan --------------------------
    y = b.section(LEFT, y, USABLE, "Insurance Company / Dental Benefit Plan Information")
    b.cell(LEFT, y, USABLE, row_h, "3", "Company / Plan Name, Address, City, State, Zip", "Box3")
    y -= row_h + 4

    # --- Other Coverage (static, for fidelity) ----------------------------
    y = b.section(LEFT, y, USABLE, "Other Coverage")
    half = USABLE / 2
    b.cell(LEFT, y, half, 18, "4", "Dental? Medical? (If both, complete 5-11)")
    b.cell(LEFT + half, y, half, 18, "5-11", "Other Subscriber / Plan Information")
    y -= 18 + 4

    # --- Policyholder / Subscriber (static) -------------------------------
    y = b.section(LEFT, y, USABLE, "Policyholder / Subscriber Information")
    b.cell(LEFT, y, USABLE, 20, "12-17", "Name, Address, Date of Birth, Subscriber ID, Plan/Group Number")
    y -= 20 + 4

    # --- Patient Information ----------------------------------------------
    y = b.section(LEFT, y, USABLE, "Patient Information")
    b.cell(LEFT, y, USABLE * 0.18, row_h, "18", "Relationship")
    b.cell(LEFT + USABLE * 0.18, y, USABLE * 0.52, row_h, "20", "Name (Last, First, Middle)", "Box20")
    b.cell(LEFT + USABLE * 0.70, y, USABLE * 0.16, row_h, "21", "Date of Birth")
    b.cell(LEFT + USABLE * 0.86, y, USABLE * 0.14, row_h, "23", "Patient ID")
    y -= row_h + 4

    # --- Record of Services Provided (table) ------------------------------
    y = b.section(LEFT, y, USABLE, "Record of Services Provided")
    cols = [
        ("24", "Procedure Date", 0.16, "Box24"),
        ("25", "Area", 0.07, None),
        ("26", "Tooth Sys.", 0.08, None),
        ("27", "Tooth Number(s)", 0.12, None),
        ("28", "Surface", 0.09, None),
        ("29", "Procedure Code", 0.14, "Box29"),
        ("30", "Description", 0.22, None),
        ("31", "Fee", 0.12, "Box31"),
    ]
    head_h = 16
    cx = LEFT
    for num, label, frac, _ in cols:
        w = USABLE * frac
        pdf.setFillGray(0.92)
        pdf.rect(cx, y - head_h, w, head_h, stroke=1, fill=1)
        pdf.setFillGray(0.0)
        pdf.setFont("Helvetica-Bold", 5.5)
        pdf.drawString(cx + 2, y - 7, num)
        pdf.setFont("Helvetica", 5)
        pdf.drawString(cx + 2, y - 13, label[:18])
        cx += w
    y -= head_h
    # one fillable data row
    data_h = 18
    cx = LEFT
    for num, label, frac, field in cols:
        w = USABLE * frac
        b.cell(cx, y, w, data_h, "", "", field, font_size=8)
        cx += w
    y -= data_h
    # total fee
    b.cell(LEFT + USABLE * 0.78, y, USABLE * 0.22, 16, "32", "Total Fee")
    y -= 16 + 4

    # --- Remarks ----------------------------------------------------------
    y = b.section(LEFT, y, USABLE, "Remarks")
    remarks_h = 1.4 * inch
    b.cell(LEFT, y, USABLE, remarks_h, "35", "Remarks", "Box35", multiline=True, font_size=9)
    y -= remarks_h + 4

    # --- Billing Dentist or Dental Entity ---------------------------------
    y = b.section(LEFT, y, USABLE, "Billing Dentist or Dental Entity")
    bill_h = 46
    b.cell(LEFT, y, USABLE * 0.55, bill_h, "48", "Name, Address, City, State, Zip",
           "Box48", multiline=True, font_size=8)
    rx = LEFT + USABLE * 0.55
    rw = USABLE * 0.45
    b.cell(rx, y, rw, bill_h / 2, "49", "NPI", "Box49", font_size=8)
    b.cell(rx, y - bill_h / 2, rw / 2, bill_h / 2, "50", "License No.", "Box50", font_size=8)
    b.cell(rx + rw / 2, y - bill_h / 2, rw / 2, bill_h / 2, "52", "Phone", "Box52", font_size=8)
    y -= bill_h + 4

    # --- Treating Dentist -------------------------------------------------
    y = b.section(LEFT, y, USABLE, "Treating Dentist and Treatment Location Information")
    treat_h = 30
    b.cell(LEFT, y, USABLE * 0.7, treat_h, "53", "Signature / Treating Dentist", "Box53", font_size=9)
    b.cell(LEFT + USABLE * 0.7, y, USABLE * 0.3, treat_h, "54", "NPI", "Box54", font_size=8)
    y -= treat_h

    pdf.showPage()
    pdf.save()

    missing = expected - b.fields_drawn
    if missing:
        raise SystemExit(f"Mapping fields not placed on the form: {sorted(missing)}")
    print(f"Wrote {OUTPUT_PATH} with {len(b.fields_drawn)} fillable fields.")


if __name__ == "__main__":
    main()
