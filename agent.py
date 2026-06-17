"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Use the LLM to extract structured search parameters from the user's
    natural language query.

    Returns a dict with keys:
        description (str):        keywords describing the item
        size        (str | None): size string if mentioned, else None
        max_price   (float | None): price ceiling if mentioned, else None

    Falls back to regex extraction if the LLM response cannot be parsed,
    and to safe defaults (None) if neither method finds a value.
    """
    prompt = (
        "Extract search parameters from the following thrift shopping query. "
        "Return ONLY a JSON object with exactly three keys:\n"
        '  "description": a short keyword string describing the item the user wants,\n'
        '  "size": the clothing size they mention (e.g. "M", "L", "W30"), or null if not mentioned,\n'
        '  "max_price": the maximum price as a number, or null if not mentioned.\n\n'
        f'Query: "{query}"\n\n'
        "Return only the JSON object. No explanation, no markdown, no extra text."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.0,           # deterministic — parsing is not creative
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # Strip accidental markdown fences if present
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

        parsed = json.loads(raw)
        return {
            "description": str(parsed.get("description") or "").strip() or query,
            "size":        parsed.get("size") or None,
            "max_price":   float(parsed["max_price"]) if parsed.get("max_price") else None,
        }

    except Exception:
        # Regex fallback so the agent never crashes on a parse failure
        price_match = re.search(r"\$(\d+(?:\.\d+)?)", query)
        size_match  = re.search(
            r"\b(XXS|XS|S/M|M/L|L/XL|XS|S|M|L|XL|XXL|W\d{2}(?:\s*L\d{2})?|US\s*\d+(?:\.\d+)?)\b",
            query,
            re.IGNORECASE,
        )
        return {
            "description": query,
            "size":        size_match.group(0).strip() if size_match else None,
            "max_price":   float(price_match.group(1)) if price_match else None,
        }


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query":             query,   # original user query
        "parsed":            {},      # extracted description / size / max_price
        "search_results":    [],      # list of matching listing dicts
        "selected_item":     None,    # top result, passed into suggest_outfit
        "wardrobe":          wardrobe,# user's wardrobe dict
        "outfit_suggestion": None,    # string returned by suggest_outfit
        "fit_card":          None,    # string returned by create_fit_card
        "error":             None,    # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    Planning loop (matches planning.md):
        Step 1  — Initialise session
        Step 2  — Parse query → description, size, max_price
        Step 3  — search_listings(); early return on empty results
        Step 4  — Select top result as selected_item
        Step 5  — suggest_outfit(); early return on empty string
        Step 6  — create_fit_card(); early return on error string
        Step 7  — Return completed session
    """

    # ── Step 1: Initialise session ────────────────────────────────────────────
    session = _new_session(query, wardrobe)

    # ── Step 2: Parse the query ───────────────────────────────────────────────
    session["parsed"] = _parse_query(query)
    description = session["parsed"]["description"]
    size        = session["parsed"]["size"]
    max_price   = session["parsed"]["max_price"]

    # ── Step 3: Search listings ───────────────────────────────────────────────
    results = search_listings(description=description, size=size, max_price=max_price)
    session["search_results"] = results

    if not results:
        filters = []
        if size:
            filters.append(f"size {size}")
        if max_price is not None:
            filters.append(f"under ${max_price:.0f}")
        filter_str = " and ".join(filters)
        hint = f" with filters: {filter_str}" if filter_str else ""
        session["error"] = (
            f"No listings found for \"{description}\"{hint}. "
            "Try broadening your search — remove the size or price limit, "
            "or use different style keywords (e.g. 'vintage' instead of 'retro')."
        )
        return session   # do NOT proceed to suggest_outfit with empty input

    # ── Step 4: Select the top result ─────────────────────────────────────────
    session["selected_item"] = results[0]

    # ── Step 5: Suggest outfit ────────────────────────────────────────────────
    outfit = suggest_outfit(new_item=session["selected_item"], wardrobe=wardrobe)
    session["outfit_suggestion"] = outfit

    if not outfit or not outfit.strip():
        session["error"] = (
            "Could not generate an outfit suggestion for this item. "
            "Try again, or check that your wardrobe data is populated."
        )
        return session

    # ── Step 6: Create fit card ───────────────────────────────────────────────
    fit_card = create_fit_card(outfit=outfit, new_item=session["selected_item"])
    session["fit_card"] = fit_card

    # create_fit_card signals failure via an "Error:" prefixed string (no exception)
    if fit_card.lower().startswith("error"):
        session["error"] = fit_card
        session["fit_card"] = None
        return session

    # ── Step 7: Return completed session ──────────────────────────────────────
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found:    {session['selected_item']['title']}")
        print(f"Parsed:   {session['parsed']}")
        print(f"\nOutfit:   {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"outfit_suggestion is None: {session2['outfit_suggestion'] is None}")
    print(f"fit_card is None:          {session2['fit_card'] is None}")

    print("\n\n=== Empty wardrobe path ===\n")
    session3 = run_agent(
        query="cozy oversized cardigan under $40",
        wardrobe=get_empty_wardrobe(),
    )
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Found:    {session3['selected_item']['title']}")
        print(f"\nOutfit (general advice): {session3['outfit_suggestion']}")
        print(f"\nFit card: {session3['fit_card']}")