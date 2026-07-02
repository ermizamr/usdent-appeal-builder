from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .automation import (
    ClinicProfile,
    build_appeal_text,
    extract_eob_data,
    generate_narrative,
)


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


def _load_template_config() -> dict:
    config_path = os.environ.get("USDENT_TEMPLATE_CONFIG", "data/ada_templates.json")
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _resolve_template(template_id: str | None, clinic_id: str | None) -> tuple[Path | None, Path | None]:
    config = _load_template_config()
    templates = config.get("templates", {})
    clinic_map = config.get("clinic_map", {})
    default_id = config.get("default_template", "default")

    selected_id = template_id or (clinic_map.get(clinic_id) if clinic_id else None) or default_id
    template = templates.get(selected_id) or templates.get(default_id)
    if not template:
        return None, None

    mapping_path = Path(template.get("mapping_path", "data/ada_form_mapping.json"))
    # An explicit env override wins (so deployments can swap in a licensed ADA
    # form); otherwise fall back to the template bundled in the repo.
    env_var = template.get("template_env", "USDENT_ADA_TEMPLATE")
    template_path = os.environ.get(env_var, "") or template.get("template_path")

    template_file = Path(template_path) if template_path else None
    if template_file and not template_file.exists():
        template_file = None
    if mapping_path and not mapping_path.exists():
        mapping_path = None
    return template_file, mapping_path


def _get_template_path() -> Path | None:
    template = os.environ.get("USDENT_ADA_TEMPLATE")
    if not template:
        return None
    path = Path(template)
    return path if path.exists() else None

app = FastAPI(title="USDENT API", version="0.1")

allowed_origins = os.getenv(
    "USDENT_UI_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/appeals")
async def create_appeal(
    file: UploadFile = File(...),
    use_ai: bool = Form(False),
    clinic_id: str | None = Form(None),
    template_id: str | None = Form(None),
) -> dict:
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        eob_data = extract_eob_data(str(temp_path))
        narrative = generate_narrative(eob_data, use_ai=use_ai)
        appeal_text = build_appeal_text(eob_data, narrative)
    except Exception as exc:  # Keep errors non-PHI, no logging of inputs.
        return JSONResponse(
            status_code=500,
            content={"error": "processing_failed", "message": str(exc)},
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    template_path, _ = _resolve_template(template_id, clinic_id)
    return {
        "extracted": {
            "patient_name": eob_data.patient_name,
            "payer_name": eob_data.payer_name,
            "provider_name": eob_data.provider_name,
            "date_of_service": eob_data.date_of_service,
            "claim_id": eob_data.claim_id,
            "procedure_code": eob_data.procedure_code,
            "denial_code": eob_data.denial_code,
            "denial_reason": eob_data.denial_reason,
            "amount_billed": eob_data.amount_billed,
            "amount_denied": eob_data.amount_denied,
        },
        "narrative": narrative,
        "appeal_text": appeal_text,
        "pdf_available": bool(template_path),
    }


@app.post("/api/appeals/pdf")
async def create_appeal_pdf(
    file: UploadFile = File(...),
    use_ai: bool = Form(False),
    clinic_id: str | None = Form(None),
    template_id: str | None = Form(None),
    clinic_name: str = Form(""),
    clinic_address: str = Form(""),
    clinic_city_state_zip: str = Form(""),
    clinic_phone: str = Form(""),
    clinic_npi: str = Form(""),
    clinic_license: str = Form(""),
    treating_dentist: str = Form(""),
) -> Response:
    template_path, mapping_path = _resolve_template(template_id, clinic_id)
    if not template_path:
        return JSONResponse(
            status_code=400,
            content={
                "error": "missing_template",
                "message": "USDENT_ADA_TEMPLATE is not set or the file does not exist.",
            },
        )

    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    output_path = None
    try:
        eob_data = extract_eob_data(str(temp_path))
        narrative = generate_narrative(eob_data, use_ai=use_ai)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output_file:
            output_path = Path(output_file.name)
        from .automation import fill_ada_form

        resolved_mapping = mapping_path or Path("data/ada_form_mapping.json")
        clinic = ClinicProfile(
            name=clinic_name,
            address=clinic_address,
            city_state_zip=clinic_city_state_zip,
            phone=clinic_phone,
            npi=clinic_npi,
            license=clinic_license,
            treating_dentist=treating_dentist,
        )
        fill_ada_form(
            eob_data,
            narrative,
            str(template_path),
            str(output_path),
            mapping_path=str(resolved_mapping),
            clinic=clinic,
            stamp_date=date.today().strftime("%m/%d/%Y"),
        )
        pdf_bytes = output_path.read_bytes()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": "processing_failed", "message": str(exc)},
        )
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        if output_path:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=appeal_packet.pdf"},
    )


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
