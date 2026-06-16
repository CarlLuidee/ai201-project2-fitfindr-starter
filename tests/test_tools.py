# tests/test_tools.py
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _sample_item():
    """Return the top result for a reliable query — used across multiple tests."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results, "Fixture failed: search returned no results"
    return results[0]


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_returns_string():
    """Happy path: populated wardrobe returns a non-empty outfit suggestion."""
    item = _sample_item()
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(item, wardrobe)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_suggest_outfit_references_wardrobe_pieces():
    """
    With a real wardrobe, the suggestion should mention at least one piece
    by name — confirming the LLM used the wardrobe, not just generic advice.
    """
    item = _sample_item()
    wardrobe = get_example_wardrobe()
    wardrobe_names = [w["name"].lower() for w in wardrobe["items"]]
    result = suggest_outfit(item, wardrobe).lower()
    matched = any(
        # Check for a significant word from each piece name
        any(word in result for word in name.split() if len(word) > 4)
        for name in wardrobe_names
    )
    assert matched, "Outfit suggestion did not reference any wardrobe pieces by name"

def test_suggest_outfit_empty_wardrobe_no_exception():
    """
    Failure mode: empty wardrobe must not raise — should return a non-empty
    string with general styling advice instead.
    """
    item = _sample_item()
    empty_wardrobe = get_empty_wardrobe()
    result = suggest_outfit(item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_suggest_outfit_empty_wardrobe_gives_advice():
    """
    Failure mode: the fallback string for an empty wardrobe should still
    contain useful styling language, not an error message.
    """
    item = _sample_item()
    empty_wardrobe = get_empty_wardrobe()
    result = suggest_outfit(item, empty_wardrobe).lower()
    styling_words = ["pair", "wear", "style", "look", "outfit", "jeans", "tee", "layer"]
    assert any(word in result for word in styling_words), (
        f"Empty-wardrobe fallback doesn't seem to contain styling advice: {result!r}"
    )


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    """Happy path: valid outfit and item produce a non-empty caption string."""
    item = _sample_item()
    wardrobe = get_example_wardrobe()
    outfit = suggest_outfit(item, wardrobe)
    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_create_fit_card_mentions_item_details():
    """
    Happy path: the caption should naturally mention the platform and price
    as specified in the tool contract.
    """
    item = _sample_item()
    wardrobe = get_example_wardrobe()
    outfit = suggest_outfit(item, wardrobe)
    result = create_fit_card(outfit, item).lower()
    assert item["platform"].lower() in result, "Caption missing platform name"
    assert str(int(item["price"])) in result, "Caption missing item price"

def test_create_fit_card_empty_outfit_no_exception():
    """
    Failure mode: empty outfit string must not raise — should return an
    error message string instead.
    """
    item = _sample_item()
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_create_fit_card_empty_outfit_returns_error_message():
    """
    Failure mode: the error string for an empty outfit should clearly
    communicate the problem, not produce a hallucinated caption.
    """
    item = _sample_item()
    result = create_fit_card("", item).lower()
    error_words = ["error", "missing", "incomplete", "cannot", "empty"]
    assert any(word in result for word in error_words), (
        f"Empty-outfit response doesn't look like an error message: {result!r}"
    )

def test_create_fit_card_whitespace_outfit_no_exception():
    """
    Failure mode: whitespace-only outfit string is treated the same as empty
    — should return an error message, not raise or produce a caption.
    """
    item = _sample_item()
    result = create_fit_card("   ", item)
    assert isinstance(result, str)
    result_lower = result.lower()
    error_words = ["error", "missing", "incomplete", "cannot", "empty"]
    assert any(word in result_lower for word in error_words), (
        f"Whitespace outfit response doesn't look like an error message: {result!r}"
    )