#!/usr/bin/env python3
"""Local RWS deck helpers: list, fuzzy match, shuffle/draw (inspired by tarot-oracle / arcanai)."""

from __future__ import annotations

import random
import re
from difflib import get_close_matches
from typing import Any

from tarot_agent import load_corpus, normalize_card


def all_cards() -> list[dict[str, Any]]:
    corpus = load_corpus()
    cards = list(corpus.get("cards") or [])
    if len(cards) < 78:
        raise RuntimeError(f"Unexpected corpus size: {len(cards)} (expected 78)")
    return cards


def card_names(card: dict[str, Any]) -> list[str]:
    names = [
        str(card.get("name_zh") or ""),
        str(card.get("name_en") or ""),
        *[str(a) for a in (card.get("aliases") or [])],
    ]
    return [n for n in names if n]


def fuzzy_lookup(query: str, *, cutoff: float = 0.72) -> dict[str, Any] | None:
    """Exact then fuzzy match against corpus names/aliases."""
    from tarot_agent import lookup_corpus_card

    hit = lookup_corpus_card(query)
    if hit:
        return hit

    needle = normalize_card(query).lower().strip()
    if not needle:
        return None

    # Common English typos seen in CLI input.
    needle = (
        needle.replace("swards", "swords")
        .replace("wandss", "wands")
        .replace("penticles", "pentacles")
        .replace("cups of", "of cups")
    )

    catalog: dict[str, dict[str, Any]] = {}
    for card in all_cards():
        for name in card_names(card):
            catalog[name.lower()] = card
            compact = re.sub(r"^the\s+", "", name.lower())
            compact = re.sub(r"[\s\-]+", "", compact)
            catalog[compact] = card

    if needle in catalog:
        return catalog[needle]
    compact_needle = re.sub(r"^the\s+", "", needle)
    compact_needle = re.sub(r"[\s\-]+", "", compact_needle)
    if compact_needle in catalog:
        return catalog[compact_needle]

    keys = list(catalog.keys())
    matches = get_close_matches(needle, keys, n=1, cutoff=cutoff)
    if not matches:
        matches = get_close_matches(compact_needle, keys, n=1, cutoff=max(0.6, cutoff - 0.1))
    if matches:
        return catalog[matches[0]]
    return None


def suggest_cards(query: str, n: int = 5) -> list[str]:
    needle = normalize_card(query).lower().strip()
    labels = []
    index: dict[str, str] = {}
    for card in all_cards():
        label = f"{card.get('name_zh')} / {card.get('name_en')}"
        for name in card_names(card):
            index[name.lower()] = label
        labels.append(label)
    keys = list(index.keys())
    close = get_close_matches(needle, keys, n=n, cutoff=0.5)
    seen: list[str] = []
    for key in close:
        label = index[key]
        if label not in seen:
            seen.append(label)
    return seen[:n]


def draw_cards(
    count: int,
    *,
    seed: str | None = None,
    reverse_chance: float = 0.5,
) -> list[dict[str, Any]]:
    """Draw unique cards with random upright/reversed (open-source CLI style)."""
    if count < 1:
        raise RuntimeError("Draw count must be at least 1")
    deck = all_cards()
    if count > len(deck):
        raise RuntimeError(f"Draw count {count} exceeds deck size {len(deck)}")

    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    chosen = rng.sample(deck, count)
    drawn: list[dict[str, Any]] = []
    for card in chosen:
        reversed_ = rng.random() < reverse_chance
        drawn.append(
            {
                "card_zh": str(card.get("name_zh") or ""),
                "card_en": str(card.get("name_en") or ""),
                "orientation": "逆位" if reversed_ else "正位",
                "corpus_card": card,
            }
        )
    return drawn


def format_drawn(cards: list[dict[str, Any]], positions: list[str] | None = None) -> str:
    lines = []
    for index, item in enumerate(cards, 1):
        pos = ""
        if positions and index <= len(positions):
            pos = f"【{positions[index - 1]}】"
        lines.append(
            f"{index}. {pos}{item['card_zh']} / {item['card_en']} {item['orientation']}"
        )
    return "\n".join(lines)
