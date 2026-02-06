# scripts/batch_ocr.py
import json
from pathlib import Path
from gemini_extract import extract_recipe_from_image

SCANS_DIR = Path("../scans")
OUTPUT_DIR = Path("../ocr")
OUTPUT_DIR.mkdir(exist_ok=True)

def process_all_scans():
    images = sorted(SCANS_DIR.glob("*.jpeg")) + sorted(SCANS_DIR.glob("*.jpg"))

    for img in images:
        print(f"🔄 Verwerken: {img.name}")

        recipe = extract_recipe_from_image(str(img))

        output_path = OUTPUT_DIR / f"{img.stem}.json"
        output_path.write_text(
            json.dumps(recipe, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"✅ Klaar: {output_path.name}")

if __name__ == "__main__":
    process_all_scans()
