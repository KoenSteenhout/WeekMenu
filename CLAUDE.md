# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dutch-language weekly meal planner ("Slim Weekmenu") that extracts recipes from HelloFresh PDFs and scanned recipe cards using Google Gemini AI, stores them in SQLite, generates diverse weekly menus using ingredient similarity scoring, and exports PDF output with shopping lists.

## Running the Application

All scripts must be run from the `scripts/` directory (paths are relative to it).

```bash
cd scripts

# Set Gemini API key
export GEMINI_API_KEY="..."

# Initialize database (creates data/recipes.db)
python db.py

# Import recipes from PDF cookbooks via Gemini OCR
python import_pdfs.py

# Batch OCR scanned recipe card images (scans/ → ocr/)
python batch_ocr.py

# Import OCR JSON results into database
python import_json.py

# Run the Streamlit web UI
streamlit run app.py

# Generate menu and print to console
python generate_menu.py
```

## Dependencies

No requirements.txt exists. Required packages: `streamlit`, `google-generativeai`, `google-genai`, `PyMuPDF` (imported as `fitz`), `reportlab`.

## Architecture

```
PDF files (pdf/)  →  import_pdfs.py  →  Gemini OCR  →  SQLite DB (data/recipes.db)
Scanned images (scans/)  →  batch_ocr.py  →  JSON (ocr/)  →  import_json.py  →  DB
DB  →  generate_menu.py  →  week menu + shopping list + PDF
DB  →  app.py (Streamlit UI)  →  interactive menu with PDF export
```

**Key modules:**

- `import_pdfs.py` — PDF→image extraction (PyMuPDF), Gemini vision API for recipe OCR, SHA1-based response caching (`scripts/_cache/`), fingerprint deduplication
- `batch_ocr.py` + `gemini_extract.py` — Scanned JPEG→JSON pipeline using Gemini. Uses a different Gemini client library (`google-genai` v3) than `import_pdfs.py` (`google-generativeai`)
- `import_json.py` — Batch imports JSON recipe files from `ocr/` into DB with deduplication
- `db.py` — Schema initialization and insert helpers (used by `app.py` path, but `import_pdfs.py` and `import_json.py` define their own schema bootstrap)
- `generate_menu.py` — Core menu algorithm, ingredient scaling, shopping list aggregation, PDF generation (reportlab). Contains `generate_week_menu()`, `replace_day()`, `build_shopping_list()`, `generate_weekmenu_pdf()`
- `app.py` — Streamlit web UI, delegates to `generate_menu.py`

## Key Patterns

- **Language:** All UI strings, variable names, comments, and prompts are in Dutch
- **Deduplication:** SHA1 fingerprint of `title::ingredients::steps` prevents duplicate recipe imports across all import paths
- **Gemini caching:** `import_pdfs.py` caches API responses by image content hash in `scripts/_cache/` to avoid redundant API calls
- **Serving scaling:** Recipes are scaled to `TARGET_SERVINGS` (default 4) using `parse_servings()` which handles varied formats like "2 personen" or "1-6 personen (ingrediënten hieronder zijn voor 2 personen)"
- **Menu diversity:** `generate_week_menu()` uses greedy selection maximizing ingredient similarity score between consecutive days, with title similarity filtering (threshold 0.75) to avoid near-duplicate dishes
- **Dual schema bootstrapping:** `import_pdfs.py` and `import_json.py` each define their own `ensure_tables_exist()` with `fingerprint` and `subtitle` columns, while `db.py` defines a slightly different schema (with `image_name` column, no `fingerprint`/`subtitle`). The import scripts' schema is the authoritative one for the current DB.

## Database Schema (SQLite)

Tables: `recipes` (id, title, subtitle, servings, source, fingerprint), `ingredients` (id, recipe_id, name, quantity, unit), `steps` (id, recipe_id, step_number, text), `tags` (id, name), `recipe_tags` (recipe_id, tag_id).

The database lives at `data/recipes.db` relative to project root.
