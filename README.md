# USDENT MVP

This repo starts the Dental EOB Appeal MVP with a rules-first engine and a narrative generator.
The initial rules and data are placeholders for development and wiring, not production clinical criteria.

## Structure
- src/usdent: core rules engine, narrative generator, and automation utilities
- data/rules: payer rules in JSON
- scripts/demo.py: quick smoke test
- tests: basic unit tests

## Quick start
- Run demo:
  - PowerShell: `$env:PYTHONPATH="src"; python scripts/demo.py`
- Run tests:
  - PowerShell: `$env:PYTHONPATH="src"; python -m unittest -v`

## Full flow script
- Requires an ADA blank form PDF and an EOB PDF or image.
- PowerShell:
  - `$env:PYTHONPATH="src"; python scripts/test_full_flow.py <eob.pdf> <ada_form.pdf> <output.pdf>`

## API (FastAPI)
- Install: `pip install fastapi uvicorn`
- Run: `uvicorn usdent.api:app --reload --port 8000`

Local CORS origins (optional):
- `USDENT_UI_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

Environment:
- Copy `.env.example` to `.env` and fill values (AI key optional).

ADA PDF output:
- Set `USDENT_ADA_TEMPLATE` to the path of your ADA form PDF.
- Use `scripts/list_pdf_fields.py` to list form field names for mapping.
- Configure multiple templates in `data/ada_templates.json`.
- Optional: `USDENT_TEMPLATE_CONFIG` to point to a custom template config file.

OCR settings (optional):
- `USDENT_TESSERACT_CMD` path to tesseract executable.
- `USDENT_OCR_LANG` (default: `eng`).
- `USDENT_OCR_OEM` (default: `3`).
- `USDENT_OCR_PSM` (default: `6`).
- `USDENT_OCR_SCALE` (default: `2`).

PDF OCR (optional):
- `USDENT_PDF_OCR=auto|1|0` (default: `auto`).
- `USDENT_PDF_DPI` (default: `300`).
- `USDENT_PDF_POPPLER_PATH` if using pdf2image on Windows.

## UI (Next.js)
- Install: `cd web; npm install`
- Run: `cd web; npm run dev`
- Configure API base URL: `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`)

## Hosting demo (no credit card)
Recommended: Render (API) + Vercel (UI).

Render (API):
1) Push this repo to GitHub.
2) In Render, create a new Web Service from the repo.
3) Render will pick up `render.yaml` automatically. If not, set:
  - Build: `apt-get update && apt-get install -y tesseract-ocr poppler-utils && pip install -r requirements.txt`
  - Start: `PYTHONPATH=src USDENT_TESSERACT_CMD=/usr/bin/tesseract uvicorn usdent.api:app --host 0.0.0.0 --port $PORT`
4) Set env vars:
  - `USDENT_UI_ORIGINS=https://<your-vercel-app>.vercel.app`
  - `LLAMA_API_KEY` (for AI narratives)
  - `USDENT_AI_MODEL=llama-3.3-70b-versatile`
  - `USDENT_AI_ENDPOINT=https://api.groq.com/openai/v1/chat/completions`

Vercel (UI):
1) Import the repo and set Root Directory to `web`.
2) Set `NEXT_PUBLIC_API_BASE_URL` to your Render API URL.
3) Deploy.

Note: Free tiers may sleep when idle; the first request can take a few seconds.

## Next steps
- Replace placeholder rules with real payer-specific denial codes and evidence requirements.
- Add OCR and EOB ingestion pipeline.
- Add ADA form mapping and packet PDF assembly.

## Automation script
The automation module provides:
- `extract_eob_data()` for PDF/image OCR extraction
- `generate_narrative()` for D2950 and D4342 denial rules
- `fill_ada_form()` for mapping into ADA 2024 claim form fields
