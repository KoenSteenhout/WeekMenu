import os
import json
from pathlib import Path

from db import get_connection, ensure_tables_exist, insert_recipe as db_insert_recipe

# =========================
# Config
# =========================
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
JSON_DIR = str(PROJECT_ROOT / "ocr")  # map met .json bestanden


# =========================
# Database helpers
# =========================
def get_db():
    conn = get_connection()
    ensure_tables_exist(conn)
    return conn


# =========================
# JSON import
# =========================
def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def process_all_jsons():
    conn = get_db()

    files = sorted(
        f for f in os.listdir(JSON_DIR)
        if f.lower().endswith(".json")
    )

    if not files:
        print("⚠️ Geen JSON-bestanden gevonden")
        return

    for filename in files:
        path = os.path.join(JSON_DIR, filename)
        print(f"\n📄 Verwerken: {filename}")

        try:
            data = load_json_file(path)
        except Exception as e:
            print(f"❌ Kan JSON niet lezen ({filename}): {e}")
            continue

        # Ondersteun zowel:
        # - 1 recept per file
        # - {"recipes": [...]}
        if isinstance(data, dict) and "recipes" in data:
            recipes = data["recipes"]
        else:
            recipes = [data]

        for recipe in recipes:
            if not recipe.get("title") or not recipe.get("ingredients") or not recipe.get("steps"):
                print("⚠️ Onvolledig recept – overslaan")
                continue

            result = db_insert_recipe(conn, recipe, source=f"json:{filename}")
            if result:
                print(f"✅ Recept geïmporteerd: {recipe['title']}")
            else:
                print(f"⏭️  Duplicate overgeslagen: {recipe['title']}")

    conn.close()
    print("\n🎉 Alle JSON-bestanden geïmporteerd (met dedupe)")

# =========================
# Main
# =========================
if __name__ == "__main__":
    process_all_jsons()
