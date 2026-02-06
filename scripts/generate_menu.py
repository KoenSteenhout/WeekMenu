# scripts/generate_menu.py

import sqlite3
import random
import re
import json
import contextlib

from pathlib import Path
from collections import defaultdict

from difflib import SequenceMatcher

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
# =========================
# Config
# =========================
DB_PATH = Path("../data/recipes.db")
OUTPUT_PDF = "weekmenu.pdf"

TARGET_SERVINGS = 4  # 👈 standaard aantal personen

DAYS = [
    "Maandag", "Dinsdag", "Woensdag",
    "Donderdag", "Vrijdag", "Zaterdag", "Zondag"
]

PANTRY_PATH = Path("../data/pantry.json")

DEFAULT_PANTRY = [
    "peper", "zwarte peper", "peper en zout", "peper & zout",
    "peper en zout (naar smaak)",
    "zout",
    "olijfolie", "extra vierge olijfolie", "olijfolie*",
    "zonnebloemolie", "zonnebloemolie*",
    "boter", "[plantaardige] boter", "plantaardige boter", "roomboter",
    "sesamolie",
    "water",
]


# =========================
# Pantry helpers
# =========================
def load_pantry() -> set:
    if PANTRY_PATH.exists():
        try:
            with open(PANTRY_PATH, "r", encoding="utf-8") as f:
                items = json.load(f)
            return {item.lower().strip() for item in items}
        except (json.JSONDecodeError, TypeError):
            pass
    # Eerste keer of corrupt bestand: schrijf defaults weg
    save_pantry(DEFAULT_PANTRY)
    return {item.lower().strip() for item in DEFAULT_PANTRY}


def save_pantry(items: list):
    PANTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PANTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(items), f, ensure_ascii=False, indent=2)


def get_all_ingredient_names() -> list:
    with contextlib.closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT lower(name) FROM ingredients ORDER BY lower(name)")
        return [row[0].strip() for row in cur.fetchall()]


# =========================
# Database helpers
# =========================
def get_connection():
    return sqlite3.connect(DB_PATH)


# =========================
# Servings parsing (ROBUST)
# =========================
def parse_servings(servings, fallback=TARGET_SERVINGS):
    """
    Normaliseert servings naar int >= 1
    Begrijpt:
    - 3
    - "2 personen"
    - "1-6 personen"
    - "1-6 personen (ingrediënten hieronder zijn voor 2 personen)"
    - "0" -> fallback
    """
    if servings is None:
        return fallback

    s = str(servings).lower().strip()
    if not s:
        return fallback

    # Expliciet: ingrediënten zijn voor X personen
    m = re.search(r"ingrediënt\w*\s+hieronder\s+zijn\s+voor\s+(\d+)", s)
    if m:
        val = int(m.group(1))
        return val if val >= 1 else fallback

    # Eerste getal nemen
    nums = re.findall(r"\d+", s)
    if not nums:
        return fallback

    val = int(nums[0])
    return val if val >= 1 else fallback


# =========================
# Quantity parsing
# =========================
def parse_quantity(qty):
    if qty is None:
        return 1.0

    if isinstance(qty, (int, float)):
        return float(qty)

    q = str(qty).strip().lower()

    try:
        return float(q.replace(",", "."))
    except ValueError:
        pass

    fractions = {"½": 0.5, "¼": 0.25, "¾": 0.75}
    for f, v in fractions.items():
        if f in q:
            base = q.replace(f, "").strip()
            try:
                return float(base) + v if base else v
            except ValueError:
                return v

    return 1.0


# =========================
# Fetch recipes
# =========================
def get_all_recipes():
    with contextlib.closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, servings FROM recipes")
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "title": r[1],
            "servings": parse_servings(r[2])
        }
        for r in rows
    ]


def get_ingredients_for_recipe(recipe_id):
    with contextlib.closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT name, quantity
            FROM ingredients
            WHERE recipe_id = ?
        """, (recipe_id,))
        rows = cur.fetchall()

    return {
        name.lower().strip(): parse_quantity(qty)
        for name, qty in rows
    }


def get_scaled_ingredients(recipe):
    """
    Geeft ingrediënten per persoon (servings-aware)
    """
    raw = get_ingredients_for_recipe(recipe["id"])
    servings = recipe.get("servings") or TARGET_SERVINGS
    if servings < 1:
        servings = TARGET_SERVINGS

    return {
        name: qty / servings
        for name, qty in raw.items()
    }


# =========================
# Title similarity helpers
# =========================
DUTCH_STOPWORDS = {"met", "en", "van", "in", "de", "het", "een", "voor", "op", "aan"}

def normalize_title(title):
    """Normalize title: lowercase, remove stopwords, sort words"""
    words = title.lower().split()
    filtered = [w for w in words if w not in DUTCH_STOPWORDS]
    return " ".join(sorted(filtered))


def title_similarity(a, b):
    # Compare both original and normalized versions
    orig_score = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    norm_score = SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()
    return max(orig_score, norm_score)


def is_similar_title(title, used_titles, threshold=0.75):
    return any(
        title_similarity(title, used) >= threshold
        for used in used_titles
    )


# =========================
# Ingredient similarity
# =========================
INGREDIENT_CATEGORIES = {
    # Proteins (5x weight)
    "kip": 5.0, "kipfilet": 5.0, "kippendij": 5.0, "kippenbouten": 5.0,
    "rund": 5.0, "rundvlees": 5.0, "rundergehakt": 5.0, "biefstuk": 5.0,
    "varken": 5.0, "varkenshaas": 5.0, "spek": 5.0, "bacon": 5.0,
    "vis": 5.0, "zalm": 5.0, "tonijn": 5.0, "kabeljauw": 5.0,
    "garnalen": 5.0, "garnaal": 5.0, "ei": 5.0, "eieren": 5.0,

    # Vegetables (3x weight)
    "tomaat": 3.0, "tomaten": 3.0, "ui": 3.0, "uien": 3.0,
    "paprika": 3.0, "courgette": 3.0, "aubergine": 3.0,
    "wortel": 3.0, "wortelen": 3.0, "broccoli": 3.0, "bloemkool": 3.0,
    "prei": 3.0, "champignons": 3.0, "champignon": 3.0,
    "spinazie": 3.0, "sla": 3.0, "kool": 3.0,

    # Spices/pantry (0.5x weight)
    "zout": 0.5, "peper": 0.5, "zwarte peper": 0.5,
    "olijfolie": 0.5, "olie": 0.5, "boter": 0.5, "water": 0.5,
    "knoflook": 0.5, "knoflookteen": 0.5,
}

def get_ingredient_weight(ingredient_name):
    """Get category weight for an ingredient (default 1.0)"""
    name_lower = ingredient_name.lower()
    for key, weight in INGREDIENT_CATEGORIES.items():
        if key in name_lower:
            return weight
    return 1.0


def is_vegetable(ingredient_name):
    """Check if an ingredient is a vegetable (weight = 3.0)"""
    weight = get_ingredient_weight(ingredient_name)
    return weight == 3.0


def calculate_vegetable_ratio(ingredients):
    """
    Calculate vegetable ratio for a recipe.
    ingredients: dict of {name: quantity} or list of names
    Returns: float between 0.0 and 1.0
    """
    if isinstance(ingredients, dict):
        ingredient_names = list(ingredients.keys())
    else:
        ingredient_names = ingredients

    if not ingredient_names:
        return 0.0

    vegetable_count = sum(1 for name in ingredient_names if is_vegetable(name))
    return vegetable_count / len(ingredient_names)


COOKING_METHODS = {
    "curry": ["curry", "kerrie"],
    "pasta": ["pasta", "spaghetti", "fusilli", "penne", "tagliatelle"],
    "stir_fry": ["wok", "roerbak"],
    "oven": ["oven", "ovenschotel"],
    "grill": ["grill", "bbq", "barbecue"],
    "soup": ["soep"],
    "salad": ["salade"],
    "risotto": ["risotto"],
    "burger": ["burger"],
}

def detect_cooking_method(title):
    """Detect cooking method from recipe title"""
    title_lower = title.lower()
    for method, keywords in COOKING_METHODS.items():
        if any(kw in title_lower for kw in keywords):
            return method
    return None


def fuzzy_ingredient_matches(ing1, ing2, threshold=0.85):
    """Find fuzzy matches between two ingredient lists"""
    matches = []
    used_ing2 = set()

    for name1 in ing1.keys():
        for name2 in ing2.keys():
            if name2 in used_ing2:
                continue
            similarity = SequenceMatcher(None, name1, name2).ratio()
            if similarity >= threshold:
                matches.append((name1, name2, similarity))
                used_ing2.add(name2)
                break
    return matches


def calculate_complexity(ingredient_count, step_count=0):
    """Calculate recipe complexity score"""
    return ingredient_count + step_count


def similarity_score(ing1, ing2, title1=None, title2=None):
    score = 0

    # Recipe complexity penalty (similar complexity = more similar feel)
    complexity1 = calculate_complexity(len(ing1))
    complexity2 = calculate_complexity(len(ing2))
    complexity_diff = abs(complexity1 - complexity2)

    # If both are complex (>12) or both simple (<6), penalize
    if (complexity1 > 12 and complexity2 > 12) or (complexity1 < 6 and complexity2 < 6):
        if complexity_diff < 3:
            score -= 5  # Penalty for similar complexity level

    # Exact matches with category weighting
    shared = set(ing1.keys()) & set(ing2.keys())
    for ing in shared:
        weight = get_ingredient_weight(ing)
        score += 2 * weight

        q1, q2 = ing1[ing], ing2[ing]
        if q1 > 0 and q2 > 0:
            score += (min(q1, q2) / max(q1, q2)) * 2 * weight

        # Bonus for common flavor ingredients
        if ing in ["peterselie", "koriander", "room", "citroen"]:
            score += 3 * weight

    # Fuzzy matches with category weighting
    remaining1 = {k: v for k, v in ing1.items() if k not in shared}
    remaining2 = {k: v for k, v in ing2.items() if k not in shared}
    fuzzy_matches = fuzzy_ingredient_matches(remaining1, remaining2)

    for name1, name2, sim in fuzzy_matches:
        weight = max(get_ingredient_weight(name1), get_ingredient_weight(name2))
        score += 1.5 * sim * weight
        q1, q2 = remaining1[name1], remaining2[name2]
        if q1 > 0 and q2 > 0:
            score += (min(q1, q2) / max(q1, q2)) * 1.5 * sim * weight

    # Carb penalty
    for carb in ["pasta", "spaghetti", "fusilli", "tagliatelle"]:
        if carb in ing1:
            score -= 1
        if carb in ing2:
            score -= 1

    # Cooking method penalty
    if title1 and title2:
        method1 = detect_cooking_method(title1)
        method2 = detect_cooking_method(title2)
        if method1 and method2 and method1 == method2:
            score -= 8  # Heavy penalty for same cooking method

    # Vegetable-poor recipe pair penalty
    veg_ratio1 = calculate_vegetable_ratio(ing1)
    veg_ratio2 = calculate_vegetable_ratio(ing2)
    LOW_VEG_THRESHOLD = 0.25  # Less than 25% vegetables
    if veg_ratio1 < LOW_VEG_THRESHOLD and veg_ratio2 < LOW_VEG_THRESHOLD:
        score -= 6  # Penalty for both recipes being low in vegetables

    return score


# =========================
# Vegetable variety tracking
# =========================
def count_unique_vegetables(menu):
    """Count unique vegetables across all recipes in menu"""
    unique_vegetables = set()

    for recipe in menu:
        ingredients = get_ingredients_for_recipe(recipe["id"])
        for ingredient_name in ingredients.keys():
            if is_vegetable(ingredient_name):
                unique_vegetables.add(ingredient_name.lower())

    return len(unique_vegetables), unique_vegetables


# =========================
# Weekmenu generator
# =========================
def generate_week_menu():
    recipes = get_all_recipes()
    if len(recipes) < 7:
        raise Exception("❗ Minder dan 7 recepten in database")

    start = random.choice(recipes)
    chosen = [start]
    used_titles = [start["title"]]

    remaining = recipes.copy()
    remaining.remove(start)

    print(f"🎯 Startgerecht: {start['title']}")

    for _ in range(6):
        last_ing = get_scaled_ingredients(chosen[-1])
        last_title = chosen[-1]["title"]

        scored = []
        for r in remaining:
            cand_ing = get_scaled_ingredients(r)
            score = similarity_score(last_ing, cand_ing, last_title, r["title"])
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)

        best = None
        for score, r in scored[:10]:
            if not is_similar_title(r["title"], used_titles, threshold=0.75):
                best = r
                break

        if best is None:
            best = scored[0][1]

        chosen.append(best)
        used_titles.append(best["title"])
        remaining.remove(best)

    # Check vegetable variety
    veg_count, vegetables = count_unique_vegetables(chosen)
    MIN_VEGETABLE_VARIETY = 15
    if veg_count < MIN_VEGETABLE_VARIETY:
        print(f"⚠️  Groentevariëteit laag: {veg_count}/{MIN_VEGETABLE_VARIETY} unieke groenten")
    else:
        print(f"✅ Goede groentevariëteit: {veg_count} unieke groenten")

    return chosen


# =========================
# Shopping list (with units)
# =========================
def build_shopping_list(menu, exclude_pantry=True):
    """
    Resultaat:
    {
      ingredient: {
        unit: hoeveelheid
      }
    }
    exclude_pantry=True filtert voorraadkast-items uit.
    """
    pantry_items = load_pantry() if exclude_pantry else set()
    shopping = defaultdict(lambda: defaultdict(float))

    # Bouw scale-factor per recipe_id
    scale_by_id = {}
    recipe_ids = []
    for r in menu:
        servings = r.get("servings") or TARGET_SERVINGS
        if servings < 1:
            servings = TARGET_SERVINGS
        scale_by_id[r["id"]] = TARGET_SERVINGS / servings
        recipe_ids.append(r["id"])

    # Eén query voor alle ingrediënten
    placeholders = ",".join("?" for _ in recipe_ids)
    with contextlib.closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT recipe_id, name, quantity, unit
            FROM ingredients
            WHERE recipe_id IN ({placeholders})
        """, recipe_ids)
        rows = cur.fetchall()

    for recipe_id, name, qty, unit in rows:
        name = name.lower().strip()
        if pantry_items and name in pantry_items:
            continue
        unit = (unit or "st").lower().strip()

        amount = parse_quantity(qty) * scale_by_id[recipe_id]
        shopping[name][unit] += amount

    return shopping


# =========================
# Debug run
# =========================
if __name__ == "__main__":
    menu = generate_week_menu()

    print("\n📅 Weekmenu:")
    for i, r in enumerate(menu, start=1):
        print(f"{i}. {r['title']} ({r['servings']} pers)")

    pantry = load_pantry()
    print(f"\n🏠 Voorraadkast: {len(pantry)} items uitgesloten")

    print("\n🛒 Boodschappenlijst:")
    shopping = build_shopping_list(menu)
    for ing, units in shopping.items():
        for unit, qty in units.items():
            print(f"- {ing}: {round(qty, 2)} {unit}")

# =========================
# Replace single day (VARIATIE!)
# =========================
def replace_day(day_index, current_menu, top_n=5):
    all_recipes = get_all_recipes()

    used_titles = {
        r["title"].lower()
        for r in current_menu
        if r is not None
    }

    neighbors = []
    if day_index > 0 and current_menu[day_index - 1]:
        neighbors.append(current_menu[day_index - 1])
    if day_index < 6 and current_menu[day_index + 1]:
        neighbors.append(current_menu[day_index + 1])

    candidates = []

    for r in all_recipes:
        if r["title"].lower() in used_titles:
            continue

        score = 0
        for n in neighbors:
            ing1 = get_ingredients_for_recipe(n["id"])
            ing2 = get_ingredients_for_recipe(r["id"])
            score += similarity_score(ing1, ing2, n["title"], r["title"])

        candidates.append((score, r))

    if not candidates:
        return current_menu

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, chosen = random.choice(candidates[:top_n])

    new_menu = current_menu.copy()
    new_menu[day_index] = chosen
    return new_menu

# =========================
# PDF helpers
# =========================
def draw_wrapped_text(c, text, x, y, max_width, line_height, font="Helvetica", font_size=11):
    c.setFont(font, font_size)
    words = text.split(" ")
    line = ""

    for word in words:
        test_line = line + word + " "
        if stringWidth(test_line, font, font_size) <= max_width:
            line = test_line
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = word + " "

    if line:
        c.drawString(x, y, line)
        y -= line_height

    return y

def get_full_recipe(recipe_id):
    with contextlib.closing(get_connection()) as conn:
        cur = conn.cursor()

        cur.execute("SELECT title, servings FROM recipes WHERE id = ?", (recipe_id,))
        row = cur.fetchone()
        if row is None:
            return None

        title, servings = row

        cur.execute("""
            SELECT name, quantity, unit
            FROM ingredients
            WHERE recipe_id = ?
        """, (recipe_id,))
        ingredients = cur.fetchall()

        cur.execute("""
            SELECT step_number, text
            FROM steps
            WHERE recipe_id = ?
            ORDER BY step_number
        """, (recipe_id,))
        steps = cur.fetchall()

    return {
        "title": title,
        "servings": parse_servings(servings),
        "ingredients": ingredients,
        "steps": steps
    }


# =========================
# PDF generation
# =========================
def generate_weekmenu_pdf(menu, filename=OUTPUT_PDF):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    margin_x = 2 * cm
    margin_y = 2 * cm
    max_width = width - 2 * margin_x

    # Page 1
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, height - margin_y, "Weekmenu")

    y = height - margin_y - 2 * cm
    for day, recipe in zip(DAYS, menu):
        y = draw_wrapped_text(
            c, f"{day} – {recipe['title']}",
            margin_x, y, max_width, 0.9 * cm, font_size=12
        )
    c.showPage()

    # Page 2
    shopping = build_shopping_list(menu)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, height - margin_y, "Boodschappenlijst")

    y = height - margin_y - 2 * cm
    for ing, units in sorted(shopping.items()):
        for unit, qty in units.items():
            line = f"{ing}: {round(qty, 2)} {unit}"
            y = draw_wrapped_text(
                c,
                line,
                margin_x,
                y,
                max_width,
                0.7 * cm
            )

            if y < margin_y:
                c.showPage()
                y = height - margin_y

    c.showPage()

    # Recipes
    for recipe in menu:
        full = get_full_recipe(recipe["id"])

        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin_x, height - margin_y, f"{full['title']} ({TARGET_SERVINGS} pers.)")

        y = height - margin_y - 2 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, "Ingrediënten")
        y -= 1 * cm

        scale = TARGET_SERVINGS / full["servings"]
        for name, qty, unit in full["ingredients"]:
            if qty:
                try:
                    qty = round(float(qty) * scale, 2)
                except (ValueError, TypeError):
                    pass
            line = f"- {name}: {qty} {unit or ''}"
            y = draw_wrapped_text(c, line, margin_x, y, max_width, 0.6 * cm)
            if y < margin_y:
                c.showPage()
                y = height - margin_y

        y -= 0.5 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, "Bereiding")
        y -= 0.8 * cm

        for nr, text in full["steps"]:
            y = draw_wrapped_text(
                c, f"{nr}. {text}",
                margin_x, y, max_width, 0.65 * cm
            )
            if y < margin_y:
                c.showPage()
                y = height - margin_y

        c.showPage()

    c.save()
    print(f"📄 PDF gegenereerd: {filename}")
