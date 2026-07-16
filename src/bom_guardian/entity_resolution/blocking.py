"""Blocking: cheap candidate generation that avoids all-to-all comparison.

Blocks used (union of pairs from each):
- normalized part-number prefix (first 6 chars)
- manufacturer part number (exact normalized)
- (category, first description token)
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import pandas as pd

from bom_guardian.entity_resolution.normalize import norm_part_number, tokens

MAX_BLOCK_SIZE = 200  # oversized blocks are skipped (uninformative keys)


def _pairs_from_blocks(blocks: dict[str, list[str]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for members in blocks.values():
        if 2 <= len(members) <= MAX_BLOCK_SIZE:
            for a, b in combinations(sorted(members), 2):
                pairs.add((a, b))
    return pairs


def generate_candidate_pairs(parts: pd.DataFrame) -> set[tuple[str, str]]:
    """Return candidate (part_id_a, part_id_b) pairs, a < b."""
    by_prefix: dict[str, list[str]] = defaultdict(list)
    by_mpn: dict[str, list[str]] = defaultdict(list)
    by_cat_token: dict[str, list[str]] = defaultdict(list)

    for _, p in parts.iterrows():
        pid = p["part_id"]
        pn = norm_part_number(p.get("source_part_number"))
        if len(pn) >= 6:
            by_prefix[pn[:6]].append(pid)
        mpn = norm_part_number(p.get("manufacturer_part_number"))
        if mpn:
            by_mpn[mpn].append(pid)
        desc_tokens = sorted(tokens(p.get("description")))
        if desc_tokens and isinstance(p.get("category"), str):
            by_cat_token[f"{p['category']}|{desc_tokens[0]}"].append(pid)

    return (
        _pairs_from_blocks(by_prefix)
        | _pairs_from_blocks(by_mpn)
        | _pairs_from_blocks(by_cat_token)
    )
