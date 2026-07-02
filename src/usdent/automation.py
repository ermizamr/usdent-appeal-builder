from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class EobData:
    patient_name: str
    date_of_service: str
    claim_id: str
    denial_code: str
    denial_reason: str
    procedure_code: str
    payer_name: str
    amount_billed: str
    amount_denied: str
    provider_name: str


@dataclass
class ClinicProfile:
    """Front-desk clinic identity used to fill billing boxes and stamp the form.

    Entered once in the UI (saved in the browser) and sent with each request, so
    the front desk only has to upload an EOB to get a clean, stamped form back.
    """

    name: str = ""
    address: str = ""
    city_state_zip: str = ""
    phone: str = ""
    npi: str = ""
    license: str = ""
    treating_dentist: str = ""

    def has_content(self) -> bool:
        return any(
            value.strip()
            for value in (
                self.name,
                self.address,
                self.city_state_zip,
                self.phone,
                self.npi,
                self.license,
                self.treating_dentist,
            )
        )

    def name_address(self) -> str:
        parts = [self.name, self.address, self.city_state_zip]
        return "\n".join(part.strip() for part in parts if part.strip())


_PATIENT_PATTERNS = [
    re.compile(r"patient\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"member\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"subscriber\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
_DOS_PATTERNS = [
    re.compile(r"date\s*of\s*service\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"service\s*date\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"\bDOS\b\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
_CLAIM_PATTERNS = [
    re.compile(r"claim\s*(id|number|#)\s*[:\-]?\s*(\S+)", re.IGNORECASE),
]
_DENIAL_REASON_PATTERNS = [
    re.compile(r"denial\s*reason\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"reason\s*code\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"adjustment\s*reason\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
_DENIAL_CODE_RE = re.compile(r"\b(?:CO-\d{2}|[A-Z]{1,2}\d{2,3})\b", re.IGNORECASE)
_PROC_CODE_RE = re.compile(r"\bD\d{4}\b", re.IGNORECASE)
_PAYER_PATTERNS = [
    re.compile(r"payer\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"insurer\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"carrier\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"plan\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
_PROVIDER_PATTERNS = [
    re.compile(r"billing\s*dentist\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"dentist\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
    re.compile(r"provider\s*name\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
_AMOUNT_RE = re.compile(r"\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})")
_AMOUNT_BILLED_LABELS = [
    "amount billed",
    "billed amount",
    "total billed",
    "amount charged",
    "total charge",
    "charges",
    "amount claimed",
    "claimed amount",
    "amount submitted",
    "submitted amount",
]
_AMOUNT_DENIED_LABELS = [
    "amount denied",
    "denied amount",
    "total denied",
    "amount disallowed",
    "disallowed amount",
    "not covered",
    "patient resp",
    "patient responsibility",
    "amount paid",
    "paid amount",
]


def _read_text_from_pdf(path: Path) -> str:
    text = _extract_text_from_pdf(path)

    ocr_mode = os.environ.get("USDENT_PDF_OCR", "auto").lower()
    if ocr_mode not in {"1", "true", "yes", "auto"}:
        return text

    if ocr_mode == "auto" and _score_text(text) >= 6:
        return text

    ocr_text = _read_text_from_pdf_images(path)
    if ocr_text:
        return f"{text}\n{ocr_text}".strip()
    return text


def _extract_text_from_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to read PDF text. Install with pip install pypdf.") from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_text_from_pdf_images(path: Path) -> str:
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return ""

    dpi = int(os.environ.get("USDENT_PDF_DPI", "300"))
    poppler_path = os.environ.get("USDENT_PDF_POPPLER_PATH")
    try:
        pages = convert_from_path(str(path), dpi=dpi, poppler_path=poppler_path)
    except Exception:
        return ""

    texts = [_ocr_image(page) for page in pages]
    return "\n".join(t for t in texts if t)


def _read_text_from_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract and pillow are required for OCR. Install with pip install pytesseract pillow."
        ) from exc

    return _ocr_image(Image.open(path))


def _read_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_eob_data(file_path: str) -> EobData:
    """Extracts key fields from a PDF or image EOB.

    This function does not log PHI. If you add logging, keep it off by default.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"EOB file not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix in {".txt"}:
        text = _read_text_from_txt(path)
    elif suffix in {".pdf"}:
        text = _read_text_from_pdf(path)
    else:
        text = _read_text_from_image(path)

    return _parse_eob_text(text)


def _parse_eob_text(text: str) -> EobData:
    patient_name = _match_first_pattern(_PATIENT_PATTERNS, text)
    date_of_service = _match_first_pattern(_DOS_PATTERNS, text)
    claim_id = _match_claim_id(text)
    denial_code = _match_denial_code(text)
    denial_reason = _match_denial_reason(text)
    procedure_code = _match_first_code(_PROC_CODE_RE, text)
    payer_name = _match_first_pattern(_PAYER_PATTERNS, text)
    if not payer_name:
        payer_name = _infer_payer_name(text)
    provider_name = _match_first_pattern(_PROVIDER_PATTERNS, text)
    amount_billed = _match_amount_by_labels(text, _AMOUNT_BILLED_LABELS)
    amount_denied = _match_amount_by_labels(text, _AMOUNT_DENIED_LABELS)

    table_row = _parse_table_row(text)
    if table_row:
        if not amount_billed:
            amount_billed = _extract_amount_from_value(
                table_row.get("amount_claimed")
                or table_row.get("amount_allowed")
                or table_row.get("amount_charged")
            )
        if not amount_denied:
            amount_denied = _extract_amount_from_value(
                table_row.get("patient_resp")
                or table_row.get("amount_paid")
                or table_row.get("amount_denied")
            )
        if not denial_code:
            denial_code = _extract_code_from_value(table_row.get("eob_code") or table_row.get("reason_code"))

    return EobData(
        patient_name=patient_name,
        date_of_service=date_of_service,
        claim_id=claim_id,
        denial_code=denial_code,
        denial_reason=denial_reason,
        procedure_code=procedure_code,
        payer_name=payer_name,
        amount_billed=amount_billed,
        amount_denied=amount_denied,
        provider_name=provider_name,
    )


def _match_or_empty(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return (match.group(1) if match.lastindex else match.group(0)).strip()


def _match_first_code(pattern: re.Pattern[str], text: str) -> str:
    matches = pattern.findall(text)
    return matches[0].upper() if matches else ""


def _match_first_pattern(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        value = _match_or_empty(pattern, text)
        if value:
            return value
    return ""


def _match_denial_reason(text: str) -> str:
    reason = _match_first_pattern(_DENIAL_REASON_PATTERNS, text)
    if reason:
        return reason
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.search(r"denied", line, re.IGNORECASE):
            return line
    return ""


def _match_denial_code(text: str) -> str:
    code = _match_or_empty(_DENIAL_CODE_RE, text).upper()
    if code:
        return code
    return _match_code_near_headers(text)


def _match_code_near_headers(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        if re.search(r"(eob|reason|adjustment).*code", line, re.IGNORECASE):
            code = _match_or_empty(_DENIAL_CODE_RE, line)
            if code:
                return code.upper()
            for offset in range(1, 3):
                if idx + offset < len(lines):
                    code = _match_or_empty(_DENIAL_CODE_RE, lines[idx + offset])
                    if code:
                        return code.upper()
    return ""


def _match_claim_id(text: str) -> str:
    for pattern in _CLAIM_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(2).strip()
    return ""


def _match_amount_by_labels(text: str, labels: list[str]) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if any(label in lower for label in labels):
            amounts = _AMOUNT_RE.findall(line)
            if amounts:
                return amounts[0].strip()
    return ""


def _split_columns(line: str) -> list[str]:
    return [col.strip() for col in re.split(r"\s{2,}", line) if col.strip()]


def _normalize_header(label: str) -> str:
    normalized = re.sub(r"\s+", " ", label.lower()).strip()
    if "amount claimed" in normalized:
        return "amount_claimed"
    if "amount allowed" in normalized:
        return "amount_allowed"
    if "amount charged" in normalized:
        return "amount_charged"
    if "patient resp" in normalized or "patient responsibility" in normalized:
        return "patient_resp"
    if "amount paid" in normalized:
        return "amount_paid"
    if "eob code" in normalized:
        return "eob_code"
    if "reason code" in normalized:
        return "reason_code"
    return normalized.replace(" ", "_")


def _looks_like_header(cols: list[str]) -> bool:
    header_text = " ".join(cols).lower()
    return "amount" in header_text and ("claimed" in header_text or "paid" in header_text)


def _parse_table_row(text: str) -> dict[str, str]:
    headers: list[str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cols = _split_columns(line)
        if _looks_like_header(cols):
            headers = [_normalize_header(col) for col in cols]
            continue
        if headers and re.search(r"\bD\d{4}\b", line, re.IGNORECASE):
            row_cols = _split_columns(line)
            if len(row_cols) < len(headers):
                row_cols.extend([""] * (len(headers) - len(row_cols)))
            return {headers[i]: row_cols[i] for i in range(len(headers))}

    # Fallback: grab any line with a procedure code and amounts
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.search(r"\bD\d{4}\b", line, re.IGNORECASE):
            amounts = _AMOUNT_RE.findall(line)
            if amounts:
                return {
                    "amount_claimed": amounts[0],
                    "amount_paid": amounts[-1],
                }
    return {}


def _extract_amount_from_value(value: str | None) -> str:
    if not value:
        return ""
    amounts = _AMOUNT_RE.findall(value)
    return amounts[0].strip() if amounts else ""


def _extract_code_from_value(value: str | None) -> str:
    if not value:
        return ""
    code = _match_or_empty(_DENIAL_CODE_RE, value)
    return code.upper() if code else ""


def _infer_payer_name(text: str) -> str:
    if re.search(r"delta\s*dental\s*ppo", text, re.IGNORECASE):
        return "Delta Dental PPO"
    if re.search(r"delta\s*dental", text, re.IGNORECASE):
        return "Delta Dental"
    if re.search(r"metlife", text, re.IGNORECASE):
        return "MetLife"
    return ""


def _configure_tesseract() -> tuple[str, str]:
    import pytesseract

    tesseract_cmd = os.environ.get("USDENT_TESSERACT_CMD")
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    lang = os.environ.get("USDENT_OCR_LANG", "eng")
    oem = os.environ.get("USDENT_OCR_OEM", "3")
    psm = os.environ.get("USDENT_OCR_PSM", "6")
    config = f"--oem {oem} --psm {psm}"
    return lang, config


def _prepare_ocr_variants(image) -> list:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    scale = int(os.environ.get("USDENT_OCR_SCALE", "2"))
    base = image.convert("RGB")
    if scale > 1:
        base = base.resize((base.width * scale, base.height * scale))

    gray = ImageOps.grayscale(base)
    contrast = ImageEnhance.Contrast(gray).enhance(1.6)
    sharp = ImageEnhance.Sharpness(contrast).enhance(1.4)
    blurred = sharp.filter(ImageFilter.MedianFilter(3))
    bw = sharp.point(lambda x: 0 if x < 180 else 255, mode="1").convert("L")

    return [base, gray, contrast, blurred, bw]


def _ocr_image(image) -> str:
    import pytesseract

    lang, config = _configure_tesseract()
    variants = _prepare_ocr_variants(image)
    texts = [pytesseract.image_to_string(variant, config=config, lang=lang) for variant in variants]
    return _select_best_text(texts)


def _score_text(text: str) -> int:
    score = 0
    if _match_first_pattern(_PATIENT_PATTERNS, text):
        score += 3
    if _match_first_pattern(_DOS_PATTERNS, text):
        score += 2
    if _match_claim_id(text):
        score += 2
    if _match_first_code(_PROC_CODE_RE, text):
        score += 2
    if _match_or_empty(_DENIAL_CODE_RE, text):
        score += 2
    if _match_first_pattern(_PAYER_PATTERNS, text) or _infer_payer_name(text):
        score += 2
    if _match_amount_by_labels(text, _AMOUNT_BILLED_LABELS):
        score += 1
    if _match_amount_by_labels(text, _AMOUNT_DENIED_LABELS):
        score += 1
    return score


def _select_best_text(texts: list[str]) -> str:
    best_text = ""
    best_score = -1
    for text in texts:
        score = _score_text(text)
        weighted = score * 10 + len(text)
        if weighted > best_score:
            best_score = weighted
            best_text = text
    return best_text


def generate_narrative(
    eob_data: EobData,
    payer_rules_path: str = "data/payer_rules.json",
    use_ai: bool = False,
    ai_model: str = "llama-3.3-70b-versatile",
    ai_endpoint: str = "https://api.groq.com/openai/v1/chat/completions",
) -> str:
    if use_ai:
        model = os.environ.get("USDENT_AI_MODEL", ai_model)
        endpoint = os.environ.get("USDENT_AI_ENDPOINT", ai_endpoint)
        rules = _load_payer_rules(payer_rules_path)
        payer_key = _normalize_payer_key(eob_data.payer_name)
        code = eob_data.procedure_code.upper()
        rule = rules.get(payer_key, {}).get(code, {})
        criteria = rule.get("required_clinical_criteria", [])
        attachments = rule.get("required_attachments", [])
        return _generate_narrative_ai(eob_data, model, endpoint, criteria, attachments)

    rules = _load_payer_rules(payer_rules_path)
    payer_key = _normalize_payer_key(eob_data.payer_name)
    code = eob_data.procedure_code.upper()

    payer_rules = rules.get(payer_key, {})
    rule = payer_rules.get(code)
    if not rule:
        return "No narrative rule matched for this procedure/payer."

    criteria = "; ".join(rule.get("required_clinical_criteria", []))
    attachments = ", ".join(rule.get("required_attachments", []))
    template = rule.get("narrative_template", "")
    return template.format(
        procedure_code=code,
        payer_name=eob_data.payer_name,
        denial_code=eob_data.denial_code,
        denial_reason=eob_data.denial_reason,
        criteria=criteria,
        attachments=attachments,
    )


def _load_payer_rules(path: str) -> Dict[str, Dict[str, Dict[str, object]]]:
    raw = Path(path).read_text(encoding="utf-8")
    return _safe_json_loads(raw)


def _safe_json_loads(raw: str) -> Dict[str, Dict[str, Dict[str, object]]]:
    import json

    return json.loads(raw)


def _normalize_payer_key(payer_name: str) -> str:
    normalized = payer_name.strip().lower().replace(" ", "_")
    if normalized.endswith("_ppo"):
        normalized = normalized.replace("_ppo", "")
    return normalized


def fill_ada_form(
    eob_data: EobData,
    narrative: str,
    template_path: str,
    output_path: str,
    mapping_path: str = "data/ada_form_mapping.json",
    clinic: Optional[ClinicProfile] = None,
    stamp_date: Optional[str] = None,
) -> None:
    """Maps extracted data and narrative into ADA claim form fields.

    When a clinic profile is supplied, its identity also fills the billing/treating
    dentist boxes and is rendered as a visible identity stamp on the form. Requires
    pypdf. Uses environment variables for any sensitive settings.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("pypdf is required to fill ADA forms. Install with pip install pypdf.") from exc

    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

    fields = _build_ada_field_map(eob_data, narrative, mapping_path, clinic)

    # No PHI logging; keep credentials in env vars only.
    _ = os.environ.get("USDENT_PHI_KEY", "")

    writer.update_page_form_field_values(writer.pages[0], fields)

    if clinic and clinic.has_content():
        _stamp_clinic_identity(writer, clinic, stamp_date)

    with open(output_path, "wb") as output_file:
        writer.write(output_file)


def _stamp_clinic_identity(writer, clinic: ClinicProfile, stamp_date: Optional[str]) -> None:
    """Overlay a rubber-stamp-style clinic identity block onto the first page."""
    overlay = _build_stamp_overlay(clinic, stamp_date)
    if overlay is None:
        return
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - guarded by caller import
        return
    stamp_page = PdfReader(overlay).pages[0]
    writer.pages[0].merge_page(stamp_page)


def _build_stamp_overlay(clinic: ClinicProfile, stamp_date: Optional[str]):
    """Render the clinic identity stamp to an in-memory PDF; None if unavailable."""
    try:
        from io import BytesIO

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
    except ImportError:
        # reportlab is optional at runtime; skip the visual stamp if missing.
        return None

    page_width, page_height = letter
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    # Position the stamp in the top-right header area, slightly rotated for a
    # hand-stamped look.
    box_w = 2.5 * inch
    box_h = 1.0 * inch
    x = page_width - box_w - 0.5 * inch
    y = page_height - box_h - 0.35 * inch

    pdf.saveState()
    pdf.translate(x + box_w / 2, y + box_h / 2)
    pdf.rotate(4)
    pdf.translate(-(box_w / 2), -(box_h / 2))

    stamp_rgb = (0.13, 0.27, 0.55)
    pdf.setStrokeColorRGB(*stamp_rgb)
    pdf.setFillColorRGB(*stamp_rgb)
    pdf.setLineWidth(1.6)
    pdf.roundRect(0, 0, box_w, box_h, 6, stroke=1, fill=0)
    pdf.setLineWidth(0.6)
    pdf.roundRect(3, 3, box_w - 6, box_h - 6, 5, stroke=1, fill=0)

    cx = box_w / 2
    text_y = box_h - 16
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawCentredString(cx, text_y, (clinic.name or "DENTAL CLINIC").upper()[:34])
    text_y -= 12

    pdf.setFont("Helvetica", 6.5)
    detail_lines = []
    npi_lic = " | ".join(
        part for part in (
            f"NPI {clinic.npi}" if clinic.npi.strip() else "",
            f"Lic {clinic.license}" if clinic.license.strip() else "",
        ) if part
    )
    if npi_lic:
        detail_lines.append(npi_lic)
    addr = ", ".join(
        part.strip() for part in (clinic.address, clinic.city_state_zip) if part.strip()
    )
    if addr:
        detail_lines.append(addr[:48])
    if clinic.phone.strip():
        detail_lines.append(f"Tel {clinic.phone.strip()}")
    for line in detail_lines[:3]:
        pdf.drawCentredString(cx, text_y, line)
        text_y -= 9

    if stamp_date:
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawCentredString(cx, 7, f"RECEIVED {stamp_date}")

    pdf.restoreState()
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def build_appeal_text(eob_data: EobData, narrative: str) -> str:
    return (
        "Appeal Packet\n"
        "============\n\n"
        f"Patient: {eob_data.patient_name}\n"
        f"Payer: {eob_data.payer_name}\n"
        f"Provider: {eob_data.provider_name}\n"
        f"Date of Service: {eob_data.date_of_service}\n"
        f"Claim ID: {eob_data.claim_id}\n"
        f"Procedure Code: {eob_data.procedure_code}\n"
        f"Denial Code: {eob_data.denial_code}\n"
        f"Denial Reason: {eob_data.denial_reason}\n"
        f"Amount Billed: {eob_data.amount_billed}\n"
        f"Amount Denied: {eob_data.amount_denied}\n\n"
        "Narrative\n"
        "---------\n"
        f"{narrative}\n"
    )


def _generate_narrative_ai(
    eob_data: EobData,
    model: str,
    endpoint: str,
    criteria: list[str],
    attachments: list[str],
) -> str:
    import json
    import urllib.request
    import urllib.error

    api_key = os.environ.get("LLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("LLAMA_API_KEY is not set. Set it in your environment before calling AI.")

    criteria_text = "; ".join(criteria) if criteria else ""
    attachments_text = ", ".join(attachments) if attachments else ""

    prompt = (
        "Write a concise dental appeal narrative (120-180 words). "
        "Use only the facts provided and do not include placeholders or bracketed text. "
        "Explicitly reference the listed clinical criteria and mention the attachments.\n\n"
        f"Payer: {eob_data.payer_name}\n"
        f"Procedure Code: {eob_data.procedure_code}\n"
        f"Denial Code: {eob_data.denial_code}\n"
        f"Denial Reason: {eob_data.denial_reason}\n"
        f"Clinical Criteria: {criteria_text}\n"
        f"Attachments: {attachments_text}\n"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a dental claims appeal assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 260,
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "USDENT/0.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        raise RuntimeError(f"AI request failed with HTTP {exc.code}: {error_body}") from exc

    return data["choices"][0]["message"]["content"].strip()


def _build_ada_field_map(
    eob_data: EobData,
    narrative: str,
    mapping_path: str,
    clinic: Optional[ClinicProfile] = None,
) -> Dict[str, str]:
    raw = Path(mapping_path).read_text(encoding="utf-8")
    mapping = _safe_json_loads(raw)
    fields: Dict[str, str] = {}

    clinic = clinic or ClinicProfile()
    # Prefer the clinic profile for the treating dentist; fall back to whatever
    # the OCR scraped off the EOB.
    treating = clinic.treating_dentist.strip() or eob_data.provider_name

    value_map = {
        "type_of_transaction": "Request for Reconsideration",
        "patient_name": eob_data.patient_name,
        "claim_id": eob_data.claim_id,
        "payer_name": eob_data.payer_name,
        "billing_dentist_name": clinic.name or eob_data.provider_name,
        "procedure_date": eob_data.date_of_service,
        "procedure_code": eob_data.procedure_code,
        "amount_billed": eob_data.amount_billed,
        "remarks": narrative,
        "clinic_name_address": clinic.name_address(),
        "clinic_npi": clinic.npi,
        "clinic_license": clinic.license,
        "clinic_phone": clinic.phone,
        "treating_dentist": treating,
    }

    for field in mapping.get("fields", []):
        pdf_field = field.get("pdf_field")
        source = field.get("source")
        if not pdf_field or not source:
            continue
        fields[pdf_field] = value_map.get(source, "")

    return fields
