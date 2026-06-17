"""
run_interaction.py

Milestone 4 manual test — runs the two example interactions from planning.md.
Place this file in the project root and run:

    python run_interaction.py
"""

from agent import run_agent
from utils.data_loader import get_example_wardrobe

# ── Happy path ────────────────────────────────────────────────────────────────
print("=" * 60)
print("HAPPY PATH: vintage graphic tee under $30")
print("=" * 60)

session = run_agent(
    query="I am looking for a vintage graphic tee under $30",
    wardrobe=get_example_wardrobe(),
)

print("\n--- PARSED QUERY ---")
print(session["parsed"])

print("\n--- SELECTED ITEM ---")
item = session["selected_item"]
if item:
    print(f"{item['title']} — ${item['price']} ({item['platform']}, {item['condition']})")

print("\n--- OUTFIT SUGGESTION ---")
print(session["outfit_suggestion"])

print("\n--- FIT CARD ---")
print(session["fit_card"])

print("\n--- ERROR ---")
print(session["error"])

# ── No-results path ───────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("NO-RESULTS PATH: designer ballgown size XXS under $5")
print("=" * 60)

session2 = run_agent(
    query="designer ballgown size XXS under $5",
    wardrobe=get_example_wardrobe(),
)

print("\n--- ERROR ---")
print(session2["error"])
print("\n--- outfit_suggestion is None:", session2["outfit_suggestion"] is None)
print("--- fit_card is None:         ", session2["fit_card"] is None)