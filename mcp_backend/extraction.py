"""Heuristic (non-LLM) extraction of individual product requests out of a
free-text customer query, e.g. "I need a 90mm stormwater flex and a roll of
PTFE tape" -> two itemized requests. This mock has no LLM wired in, so
splitting/attribute-tagging is done with keyword and regex heuristics -- good
enough to shape-test an agent integration against the real contract, not a
substitute for genuine NL understanding.
"""
import re
from functools import lru_cache
from pathlib import Path

import yaml

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"

_PREAMBLE_RE = re.compile(
    r"^\s*(?:"
    r"i(?:'d| would)?\s+(?:need|want|require|like|am after|am looking for)|"
    r"can\s+i\s+(?:get|have|grab)|could\s+i\s+(?:get|have|grab)|"
    r"give\s+me|looking\s+for|please\s+(?:get|send|find)\s+me"
    r")\s+",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(r"\s*(?:,|;|&|\band\b|\bplus\b|\bas well as\b)\s*", re.IGNORECASE)

_QUANTITY_WORDS = {
    "a": 1, "an": 1, "one": 1, "single": 1,
    "couple": 2, "pair": 2, "two": 2,
    "few": 3, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "dozen": 12, "a dozen": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
_CONTAINER_WORDS = [
    "rolls", "roll", "tubes", "tube", "boxes", "box",
    "packs", "pack", "sets", "set", "pairs", "pair", "lengths", "length",
]
# Longest quantity word/phrase first, so "a dozen" wins over the standalone "a"
# that would otherwise greedily match its first word and strand "dozen" in the
# item name -- same fix as _find_term's longest-first vocab ordering below.
_QUANTITY_WORDS_PATTERN = "|".join(sorted(_QUANTITY_WORDS, key=len, reverse=True))
_LEADING_QTY_RE = re.compile(
    r"^(?:(\d+)\s*x?\s+|(" + _QUANTITY_WORDS_PATTERN + r")\s+)?"
    r"(?:(" + "|".join(_CONTAINER_WORDS) + r")\s+of\s+)?",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _load_attribute_vocab():
    with open(SEED_DIR / "categories.yaml") as f:
        categories = yaml.safe_load(f)["categories"]

    colors, materials = set(), set()
    for category in categories:
        for subcategory in category["subcategories"]:
            options = subcategory.get("attribute_options", {})
            colors.update(o.lower() for o in options.get("color", []))
            colors.update(o.lower() for o in options.get("finish", []))
            materials.update(o.lower() for o in options.get("material", []))
    return colors, materials


@lru_cache(maxsize=1)
def _load_unstocked_brands():
    with open(SEED_DIR / "unstocked_brands.yaml") as f:
        data = yaml.safe_load(f) or {}
    return data.get("unstocked_brands", [])


def _find_term(text_lower, vocab):
    for term in sorted(vocab, key=len, reverse=True):
        if term in text_lower:
            return term
    return ""


def _find_unstocked_brand(text_lower):
    for brand in _load_unstocked_brands():
        names = [brand["name"], *brand.get("aliases", [])]
        if any(name.lower() in text_lower for name in names):
            return brand["name"]
    return None


def _parse_span(span):
    match = _LEADING_QTY_RE.match(span)
    quantity = 1
    container = None
    remainder = span.strip()

    if match:
        if match.group(1):
            quantity = int(match.group(1))
        elif match.group(2):
            quantity = _QUANTITY_WORDS[match.group(2).lower()]
        container = match.group(3)
        remainder = span[match.end():].strip()

    colors, materials = _load_attribute_vocab()
    remainder_lower = remainder.lower()
    color = _find_term(remainder_lower, colors)
    material = _find_term(remainder_lower, materials)
    unstocked_brand = _find_unstocked_brand(remainder_lower)
    additional_context = f"{quantity} {container}" if container else ""

    hint_parts = [part for part in (material, color) if part and part not in remainder_lower]
    hint_parts.append(remainder)
    semantic_search_hint = " ".join(hint_parts)

    # A bare leading article ("a"/"one"/...) carries no information and is
    # dropped from the spoken-text span; a container phrase ("a roll of") is
    # kept since it's the customer's actual unit, not filler.
    clean_span = span.strip() if container else remainder

    return {
        "item_name": remainder,
        "quantity": quantity,
        "color": color,
        "material": material,
        "additional_context": additional_context,
        "semantic_search_hint": semantic_search_hint,
        "clean_span": clean_span,
        "unstocked_brand": unstocked_brand,
    }


def extract_items(query):
    """Split a free-text query into one entry per distinct product asked for,
    tagging each with a best-effort quantity/color/material and the literal
    query substring ("source span") it came from.
    """
    cleaned = _PREAMBLE_RE.sub("", query.strip(), count=1)
    spans = [s.strip() for s in _SPLIT_RE.split(cleaned) if s.strip()]
    if not spans:
        spans = [cleaned] if cleaned else [query.strip()]

    items = []
    for index, span in enumerate(spans):
        parsed = _parse_span(span)
        items.append(
            {
                "item_index": index,
                "item_name": parsed["item_name"],
                "quantity": parsed["quantity"],
                "color": parsed["color"],
                "material": parsed["material"],
                "additional_context": parsed["additional_context"],
                "semantic_search_hint": parsed["semantic_search_hint"],
                "source_spans": [parsed["clean_span"]],
                "unstocked_brand": parsed["unstocked_brand"],
            }
        )
    return items
