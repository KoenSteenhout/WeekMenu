import os
import json
import hashlib
import fitz  # PyMuPDF
import google.generativeai as genai
from typing import List
from pathlib import Path

from db import get_connection, ensure_tables_exist, insert_recipe as db_insert_recipe

# =========================
# Config
# =========================
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
PDF_DIR = str(PROJECT_ROOT / "pdf")
TMP_IMG_DIR = str(SCRIPT_DIR / "_tmp_pages")
CACHE_DIR = str(SCRIPT_DIR / "_cache")

os.makedirs(TMP_IMG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# API key via env var: export GEMINI_API_KEY="..."
_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY omgevingsvariabele is niet gezet. Gebruik: export GEMINI_API_KEY='...'")
genai.configure(api_key=_api_key)
MODEL = genai.GenerativeModel("gemini-2.5-flash")

PROMPT = """
Je ziet een HelloFresh recept-pagina (PDF).

Extraheer ALLE recepten op deze pagina.

Geef het resultaat EXCLUSIEF terug als geldig JSON in exact dit schema:

{
  "recipes": [
    {
      "title": "string",
      "subtitle": "string | null",
      "servings": "string | null",
      "ingredients": [
        {
          "name": "string",
          "quantity": "string | null",
          "unit": "string | null"
        }
      ],
      "steps": ["string"]
    }
  ]
}

REGELS:
- Geen uitleg
- Geen markdown
- Geen commentaar
- Alleen geldig JSON
- Als iets ontbreekt: null
"""

def get_db():
    conn = get_connection()
    ensure_tables_exist(conn)
    return conn

# =========================
# PDF → images + prefilter
# =========================
def page_has_recipe_text(page) -> bool:
    """
    Snelle tekstscan om Gemini-calls te vermijden
    """
    text = (page.get_text() or "").lower()
    return (
        "ingrediënten" in text
        or "ingredienten" in text
        or "bereiden" in text
        or "voorbereiden" in text
    )


def pdf_to_images(pdf_path: str) -> List[str]:
    doc = fitz.open(pdf_path)
    images = []

    for i, page in enumerate(doc):
        if not page_has_recipe_text(page):
            continue

        pix = page.get_pixmap(dpi=200)
        img_path = os.path.join(
            TMP_IMG_DIR,
            f"{os.path.basename(pdf_path)}_page_{i+1}.png"
        )
        pix.save(img_path)
        images.append(img_path)

    return images

# =========================
# Gemini + caching
# =========================
def cache_key_for_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def extract_recipes_from_image(image_path: str) -> List[dict]:
    cache_key = cache_key_for_image(image_path)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f).get("recipes", [])

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    try:
        response = MODEL.generate_content(
            [
                PROMPT,
                {
                    "mime_type": "image/png",
                    "data": image_bytes
                }
            ],
            generation_config={"temperature": 0}
        )
    except Exception as e:
        print(f"❌ Gemini API fout ({image_path}): {e}")
        return []

    try:
        data = json.loads(response.text)
    except Exception:
        print(f"❌ JSON parse fout ({image_path})")
        return []

    # cache resultaat
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data.get("recipes", [])

# =========================
# Main
# =========================
def process_all_pdfs():
    conn = get_db()

    for pdf in sorted(os.listdir(PDF_DIR)):
        if not pdf.lower().endswith(".pdf"):
            continue

        print(f"\n📄 Verwerken: {pdf}")
        pdf_path = os.path.join(PDF_DIR, pdf)

        images = pdf_to_images(pdf_path)

        if not images:
            print("⚠️ Geen receptpagina’s gevonden")
            continue

        for img in images:
            print(f"🤖 Analyse: {img}")
            recipes = extract_recipes_from_image(img)

            for r in recipes:
                if not r.get("ingredients") or not r.get("steps"):
                    continue
                result = db_insert_recipe(conn, r, source="pdf-gemini")
                if result:
                    print(f"✅ Recept opgeslagen: {r['title']}")

    conn.close()
    print("\n🎉 Import voltooid (met caching + dedupe)")


if __name__ == "__main__":
    process_all_pdfs()
