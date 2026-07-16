"""Pairwise similarity features. Every feature is human-interpretable and
returned by name so match evidence can be shown to stewards."""

from __future__ import annotations

from difflib import SequenceMatcher

import pandas as pd

from bom_guardian.entity_resolution.normalize import norm_part_number, norm_text, tokens

FEATURE_NAMES: list[str] = [
    "part_number_exact",
    "part_number_normalized_match",
    "part_number_char_similarity",
    "description_token_jaccard",
    "description_char_similarity",
    "mpn_match",
    "uom_compatible",
    "category_match",
    "cost_proximity",
    "source_system_differs",
    "lead_time_proximity",
]


def _char_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _proximity(a: float | None, b: float | None) -> float:
    """1.0 when equal, decaying with relative difference; 0 when unknown."""
    if a is None or b is None or pd.isna(a) or pd.isna(b):
        return 0.0
    hi, lo = max(abs(a), abs(b)), min(abs(a), abs(b))
    if hi == 0:
        return 1.0
    return max(0.0, lo / hi)


def pair_features(a: pd.Series, b: pd.Series) -> dict[str, float]:
    """Compute all similarity features for a candidate part pair."""
    pn_a, pn_b = a.get("source_part_number") or "", b.get("source_part_number") or ""
    pn_na, pn_nb = norm_part_number(pn_a), norm_part_number(pn_b)
    mpn_a = norm_part_number(a.get("manufacturer_part_number"))
    mpn_b = norm_part_number(b.get("manufacturer_part_number"))
    desc_a, desc_b = norm_text(a.get("description")), norm_text(b.get("description"))

    return {
        "part_number_exact": float(bool(pn_a) and pn_a == pn_b),
        "part_number_normalized_match": float(bool(pn_na) and pn_na == pn_nb),
        "part_number_char_similarity": _char_sim(pn_na, pn_nb),
        "description_token_jaccard": _jaccard(
            tokens(a.get("description")), tokens(b.get("description"))
        ),
        "description_char_similarity": _char_sim(desc_a, desc_b),
        "mpn_match": float(bool(mpn_a) and mpn_a == mpn_b),
        "uom_compatible": float(
            (a.get("uom") or "") == (b.get("uom") or "") or not a.get("uom") or not b.get("uom")
        ),
        "category_match": float((a.get("category") or "") == (b.get("category") or "")),
        "cost_proximity": _proximity(a.get("standard_cost"), b.get("standard_cost")),
        "source_system_differs": float(
            (a.get("source_system") or "") != (b.get("source_system") or "")
        ),
        "lead_time_proximity": _proximity(a.get("lead_time_days"), b.get("lead_time_days")),
    }
