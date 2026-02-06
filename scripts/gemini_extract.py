# scripts/gemini_extract.py
import os
from google import genai
from google.genai import types
import json

_api_key = os.environ.get("GEMINI_API_KEY")
if not _api_key:
    raise RuntimeError("GEMINI_API_KEY omgevingsvariabele is niet gezet. Gebruik: export GEMINI_API_KEY='...'")

client = genai.Client(api_key=_api_key)

HELLOFRESH_PROMPT = """
Je krijgt een foto van een HelloFresh receptkaart (Nederlands).

Extraheer de info en geef ALLEEN geldige JSON terug in deze structuur:

{
  "title": "string",
  "servings": 0,
  "ingredients": [
    { "name": "string", "quantity": 0, "unit": "g" }
  ],
  "steps": [
    "Stap 1 ...",
    "Stap 2 ..."
  ]
}

GEEN tekst buiten de JSON. GEEN uitleg.
"""

def extract_recipe_from_image(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            HELLOFRESH_PROMPT,
        ],
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    return json.loads(raw)
