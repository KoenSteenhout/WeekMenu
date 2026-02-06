# scripts/db.py
import sqlite3
import hashlib
from pathlib import Path

# Get script directory and build paths from there
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "recipes.db"


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def ensure_tables_exist(conn):
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subtitle TEXT,
            servings TEXT,
            source TEXT,
            fingerprint TEXT
        )
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_recipes_fingerprint
        ON recipes(fingerprint)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity TEXT,
            unit TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipe_tags (
            recipe_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY(recipe_id) REFERENCES recipes(id),
            FOREIGN KEY(tag_id) REFERENCES tags(id)
        )
    """)

    conn.commit()


def init_db():
    conn = get_connection()
    ensure_tables_exist(conn)
    conn.close()
    print("📦 Database is klaar.")


# =========================
# Fingerprint / dedupe
# =========================
def recipe_fingerprint(recipe: dict) -> str:
    title = (recipe.get("title") or "").strip().lower()
    ings = "|".join(
        sorted(
            (i.get("name") or "").strip().lower()
            for i in recipe.get("ingredients", [])
        )
    )
    steps = "|".join(
        (s or "").strip().lower()
        for s in recipe.get("steps", [])
    )
    raw = f"{title}::{ings}::{steps}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# =========================
# Insert helpers
# =========================
def insert_recipe(conn: sqlite3.Connection, recipe: dict, source: str = "unknown"):
    cur = conn.cursor()
    fp = recipe_fingerprint(recipe)

    cur.execute("""
        INSERT OR IGNORE INTO recipes
        (title, subtitle, servings, source, fingerprint)
        VALUES (?,?,?,?,?)
    """, (
        recipe["title"],
        recipe.get("subtitle"),
        str(recipe.get("servings")) if recipe.get("servings") is not None else None,
        source,
        fp
    ))

    if cur.rowcount == 0:
        return None

    recipe_id = cur.lastrowid

    for ing in recipe.get("ingredients", []):
        cur.execute("""
            INSERT INTO ingredients
            (recipe_id, name, quantity, unit)
            VALUES (?,?,?,?)
        """, (
            recipe_id,
            ing.get("name"),
            ing.get("quantity"),
            ing.get("unit")
        ))

    for i, step in enumerate(recipe.get("steps", []), start=1):
        cur.execute("""
            INSERT INTO steps
            (recipe_id, step_number, text)
            VALUES (?,?,?)
        """, (recipe_id, i, step))

    conn.commit()
    return recipe_id


def get_or_create_tag(conn, name):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
    conn.commit()
    cur.execute("SELECT id FROM tags WHERE name = ?", (name,))
    return cur.fetchone()[0]


def link_tag_to_recipe(conn, recipe_id, tag_id):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO recipe_tags (recipe_id, tag_id)
        VALUES (?, ?)
    """, (recipe_id, tag_id))
    conn.commit()


if __name__ == "__main__":
    init_db()
