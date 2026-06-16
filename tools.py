"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _chat(prompt: str, temperature: float = 0.7) -> str:
    """Send a prompt to Groq and return the response text."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    listings = load_listings()
    desc_lower = description.lower()

    # Step 1 — Hard filters: price and size
    candidates = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None:
            # Accept if the provided size appears anywhere in the listing's size
            # string (e.g. "M" matches "S/M", "One Size / Oversized", etc.)
            if size.strip().lower() not in item["size"].strip().lower():
                continue
        candidates.append(item)

    # Step 2 — Score each candidate by keyword overlap with description
    def score(item: dict) -> int:
        s = 0
        # Style tags are the strongest signal — each match is worth 2 points
        for tag in item.get("style_tags", []):
            if tag.lower() in desc_lower:
                s += 2
        # Color mentions
        for color in item.get("colors", []):
            if color.lower() in desc_lower:
                s += 1
        # Category keyword
        if item.get("category", "").lower() in desc_lower:
            s += 1
        # Individual words from the title (skip very short words)
        for word in item.get("title", "").lower().split():
            if len(word) > 3 and word in desc_lower:
                s += 1
        # Words from the listing description field
        for word in item.get("description", "").lower().split():
            if len(word) > 4 and word in desc_lower:
                s += 1
        return s

    # Step 3 — Drop zero-score items, sort by score descending
    scored = [(score(item), item) for item in candidates]
    scored = [(s, item) for s, item in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offers general styling advice for the item.
    """
    wardrobe_items: list[dict] = wardrobe.get("items", [])

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Description: {new_item.get('description', '')}"
    )

    # Empty wardrobe — ask for general styling advice only
    if not wardrobe_items:
        prompt = (
            "You are a thrift fashion stylist. A user is considering buying the following item "
            "but hasn't shared their wardrobe yet.\n\n"
            f"{item_summary}\n\n"
            "Give them 1–2 specific outfit ideas using common wardrobe staples (basic denim, "
            "white tee, sneakers, etc.). Be concrete and casual — like advice from a stylish friend, "
            "not a fashion magazine. Keep it to 3–5 sentences."
        )
        return _chat(prompt, temperature=0.7)

    # Format wardrobe for the prompt
    wardrobe_lines = []
    for w in wardrobe_items:
        line = (
            f"- {w.get('name', 'item')} "
            f"({w.get('category', '')}; "
            f"colors: {', '.join(w.get('colors', []))}; "
            f"tags: {', '.join(w.get('style_tags', []))})"
        )
        if w.get("notes"):
            line += f" — {w['notes']}"
        wardrobe_lines.append(line)

    wardrobe_text = "\n".join(wardrobe_lines)

    prompt = (
        "You are a thrift fashion stylist. A user wants to buy the item below and needs outfit "
        "ideas using pieces they already own.\n\n"
        f"NEW ITEM:\n{item_summary}\n\n"
        f"THEIR WARDROBE:\n{wardrobe_text}\n\n"
        "Suggest 1–2 complete outfits that incorporate the new item and specific named pieces "
        "from their wardrobe. Be concrete — name each piece. Add one brief styling tip per outfit "
        "(tuck, layer, roll, etc.). Keep the tone casual and friendly, 4–6 sentences total."
    )
    return _chat(prompt, temperature=0.7)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, returns a descriptive error message
        string — does NOT raise an exception.
    """
    # Guard: empty or whitespace-only outfit
    if not outfit or not outfit.strip():
        return (
            "Error: cannot generate a fit card because the outfit description is missing "
            "or incomplete. Please ensure suggest_outfit ran successfully first."
        )

    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price")
    platform = new_item.get("platform", "a thrift app")
    condition = new_item.get("condition", "")
    style_tags = new_item.get("style_tags", [])

    price_str = f"${price:.0f}" if price is not None else "a great price"
    condition_str = f"{condition} condition" if condition else "great condition"
    tags_str = ", ".join(style_tags) if style_tags else "vintage thrift"

    prompt = (
        "You are writing an Instagram/TikTok OOTD caption for a thrift find. "
        "Make it feel real, casual, and specific — like an actual person posting, not a brand.\n\n"
        f"Item: {title}\n"
        f"Price: {price_str} from {platform} ({condition_str})\n"
        f"Style vibe: {tags_str}\n"
        f"Outfit: {outfit}\n\n"
        "Write a caption that:\n"
        "- Is 2–4 sentences long\n"
        "- Mentions the item name, price, and platform naturally (once each)\n"
        "- Captures the outfit vibe in specific, evocative terms\n"
        "- Sounds authentic and slightly informal (contractions, maybe one emoji)\n"
        "- Ends with a teaser like 'full look in my stories' or similar\n"
        "Return only the caption text, nothing else."
    )
    return _chat(prompt, temperature=0.9)