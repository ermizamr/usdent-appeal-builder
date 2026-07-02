---
title: USDENT API
emoji: 🦷
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

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
- Works out of the box: a fillable ADA-style claim form is bundled at `data/ada_claim_template.pdf` and used by default, so the "Download ADA PDF" button is always enabled.
- This bundled form is an ADA-style facsimile, not the copyrighted official ADA form. To use a licensed official form, set `USDENT_ADA_TEMPLATE` to its path (the env override takes priority over the bundled template).
- Regenerate the bundled template with `python scripts/generate_ada_template.py` (requires `reportlab`).
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
Recommended: Hugging Face Spaces (API, Docker) + Vercel (UI).

Hugging Face Space (API):
1) Create a new Space at https://huggingface.co/new-space with **SDK: Docker** (blank template).
2) Push this repo to the Space's git remote (the Space reads the Docker metadata
   from this README's YAML header and builds the `Dockerfile`; it serves on port `7860`).
   - `git remote add space https://huggingface.co/spaces/<user>/<space-name>`
   - `git push space main`
3) In the Space, open **Settings → Variables and secrets** and add:
  - Secret `LLAMA_API_KEY` (for AI narratives)
  - Variable `USDENT_UI_ORIGINS=https://<your-vercel-app>.vercel.app`
  - Variable `USDENT_AI_MODEL=llama-3.3-70b-versatile`
  - Variable `USDENT_AI_ENDPOINT=https://api.groq.com/openai/v1/chat/completions`
  - Variable `USDENT_TESSERACT_CMD=/usr/bin/tesseract`
  - Variable `USDENT_PDF_OCR=auto`
  - Variable `USDENT_PDF_DPI=300`
4) The API is then served at `https://<user>-<space-name>.hf.space`
   (health check: `GET /health`).

Vercel (UI):
1) Import the repo and set Root Directory to `web`.
2) Set `NEXT_PUBLIC_API_BASE_URL` to your Space URL (`https://<user>-<space-name>.hf.space`).
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
