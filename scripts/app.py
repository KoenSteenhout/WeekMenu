import streamlit as st
from generate_menu import (
    generate_week_menu,
    replace_day,
    generate_weekmenu_pdf,
    build_shopping_list,
    load_pantry,
    save_pantry,
    get_all_ingredient_names,
    DEFAULT_PANTRY,
    TARGET_SERVINGS,
)

DAYS = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]

st.set_page_config(page_title="Slim Weekmenu", layout="centered")

st.title("🍽️ Slim Weekmenu")
st.caption(f"Menu voor {TARGET_SERVINGS} personen")

if "menu" not in st.session_state:
    try:
        st.session_state.menu = generate_week_menu()
    except Exception:
        st.error("Niet genoeg recepten in de database (minimaal 7 nodig). Importeer eerst recepten.")
        st.stop()

st.subheader("📅 Weekmenu")

for i, recipe in enumerate(st.session_state.menu):
    col1, col2, col3 = st.columns([6, 1, 1])

    col1.markdown(f"**{DAYS[i]}**  \n{recipe['title']}")

    if col2.button("↻", key=f"regen_{i}"):
        st.session_state.menu = replace_day(i, st.session_state.menu)
        st.rerun()

    if col3.button("✖", key=f"remove_{i}"):
        new_menu = st.session_state.menu.copy()
        new_menu[i] = None
        st.session_state.menu = new_menu
        st.rerun()

st.divider()

if st.button("🔄 Volledig nieuw menu"):
    try:
        st.session_state.menu = generate_week_menu()
        st.rerun()
    except Exception:
        st.error("Niet genoeg recepten in de database (minimaal 7 nodig).")

if st.button("📄 Exporteer naar PDF"):
    if None in st.session_state.menu:
        st.warning("Menu bevat lege dagen")
    else:
        try:
            generate_weekmenu_pdf(st.session_state.menu)
            st.success("PDF gegenereerd!")
        except Exception as e:
            st.error(f"Fout bij PDF-generatie: {e}")

# =========================
# Boodschappenlijst
# =========================
if None not in st.session_state.menu:
    st.subheader("🛒 Boodschappenlijst")
    shopping = build_shopping_list(st.session_state.menu)
    for ing, units in sorted(shopping.items()):
        for unit, qty in units.items():
            st.write(f"- {ing}: {round(qty, 2)} {unit}")

# =========================
# Voorraadkast beheren
# =========================
with st.expander("🏠 Voorraadkast beheren"):
    all_names = get_all_ingredient_names()
    current_pantry = sorted(load_pantry())

    selected = st.multiselect(
        "Ingrediënten in voorraad (worden uitgesloten van boodschappenlijst)",
        options=all_names,
        default=[item for item in current_pantry if item in all_names],
        key="pantry_select",
    )

    if set(selected) != set(current_pantry):
        save_pantry(selected)
        st.rerun()

    if st.button("Herstel standaardlijst"):
        save_pantry(DEFAULT_PANTRY)
        st.rerun()

st.caption("👨‍🍳 Slimme menuplanning met servings-correctie")
