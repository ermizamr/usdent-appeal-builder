import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:
    raise SystemExit("pypdf is required. Install with pip install pypdf.") from exc


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/list_pdf_fields.py <template.pdf>")

    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}

    if not fields:
        print("No form fields found in the PDF.")
        return

    for name, field in fields.items():
        value = field.get("/V") if isinstance(field, dict) else None
        print(f"{name} = {value}")


if __name__ == "__main__":
    main()
