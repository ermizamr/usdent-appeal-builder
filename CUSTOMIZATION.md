# Front Desk Customization Guide

## Simple Workflow

**Your job as front desk staff:**
1. Upload a messy paper EOB (scan/photo)
2. Click "Generate Clean Appeal Form"  
3. Download the clean, filled ADA form
4. Print and send

That's it! No data entry, no forms to fill manually.

## Customizing for Your Clinic

### Option 1: Use Your Own ADA Form Template (Recommended)

If you have a licensed official ADA form PDF:

1. Open `.env` file in the project root
2. Set the path to your form:
   ```
   USDENT_ADA_TEMPLATE=path/to/your/ada_form.pdf
   ```
3. The form must have fillable fields matching the boxes in `data/ada_form_mapping.json`

### Option 2: Add Clinic-Specific Templates

For multiple clinics with different forms:

1. Edit `data/ada_templates.json`
2. Add your clinic:
   ```json
   {
     "templates": {
       "clinic_alpha": {
         "display_name": "Alpha Dental",
         "template_path": "data/forms/alpha_ada.pdf",
         "mapping_path": "data/ada_form_mapping.json"
       }
     },
     "clinic_map": {
       "alpha": "clinic_alpha"
     }
   }
   ```
3. Front desk enters clinic ID "alpha" when uploading

### Option 3: Customize the Field Mapping

If your form has different field names:

1. Run `python scripts/list_pdf_fields.py your_form.pdf` to see all field names
2. Edit `data/ada_form_mapping.json` to match your form's field names
3. The system will auto-fill those fields

## What Gets Filled Automatically

From the uploaded EOB, the system extracts and fills:
- **Box 1**: Type of Transaction → "Request for Reconsideration"
- **Box 3**: Patient Name
- **Box 5**: Claim ID
- **Box 10**: Insurance Company Name
- **Box 11**: Billing Dentist/Provider Name
- **Box 24**: Procedure Date
- **Box 26**: Procedure Code
- **Box 28**: Fee/Amount Billed
- **Box 35**: Appeal Narrative (auto-generated based on denial reason)

## Real-World Experience

The system is designed for typical front desk workflows:
- Works with poor-quality scans and phone photos
- Handles handwritten or typed EOBs
- Extracts key info even from messy layouts
- Generates professional appeal language automatically
- Outputs a clean, printable ADA form ready to mail/fax

No special software or training needed!
