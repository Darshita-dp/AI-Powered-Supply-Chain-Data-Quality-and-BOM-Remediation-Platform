"""BOM structure generators: headers, components, revisions, ECOs, substitutions,
supersessions.

Hierarchy realism without cycles: parts carry a `bom_tier` (0=raw component ...
3=finished good). Parents only reference children from strictly lower tiers, which
guarantees the clean baseline is a DAG. Cycles are introduced later, deliberately,
by the issue injector (M3) — never here.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from data_generator.generators.context import GenContext


def generate_bom(
    ctx: GenContext, parts: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (bom_headers, bom_components, engineering_revisions)."""
    assemblies = parts[parts["bom_tier"] >= 1]
    n_assemblies = min(len(assemblies), int(len(parts) * ctx.cfg.assembly_ratio))
    assemblies = assemblies.sample(n=n_assemblies, random_state=int(ctx.rng.integers(0, 2**31)))

    by_tier: dict[int, list[str]] = {
        t: parts.loc[parts["bom_tier"] == t, "part_id"].tolist() for t in range(4)
    }

    headers, components, revisions = [], [], []
    comp_key = 0
    rev_key = 0
    for h, (_, asm) in enumerate(assemblies.iterrows(), start=1):
        tier = int(asm["bom_tier"])
        candidate_children: list[str] = []
        for t in range(tier):
            candidate_children.extend(by_tier[t])
        if not candidate_children:
            continue

        n_revs = max(1, int(ctx.rng.poisson(ctx.cfg.revisions_per_assembly - 1) + 1))
        base_date = ctx.past_date(max_days=2000, min_days=200)
        header_id = f"BOM{h:06d}"
        headers.append(
            {
                "bom_header_id": header_id,
                "parent_part_id": asm["part_id"],
                "plant_code": asm["primary_plant"],
                "bom_usage": "PRODUCTION",
                "status": "ACTIVE" if asm["lifecycle_status"] == "ACTIVE" else "INACTIVE",
                "created_date": base_date,
            }
        )

        n_comp = max(2, int(ctx.rng.poisson(ctx.cfg.avg_components_per_bom)))
        chosen = ctx.rng.choice(
            candidate_children, size=min(n_comp, len(candidate_children)), replace=False
        )
        for rev_i in range(n_revs):
            rev_key += 1
            rev_label = chr(ord("A") + rev_i)
            eff_from = base_date + timedelta(days=rev_i * int(ctx.rng.integers(90, 400)))
            eff_to = (
                base_date + timedelta(days=(rev_i + 1) * int(ctx.rng.integers(90, 400)) - 1)
                if rev_i < n_revs - 1
                else None
            )
            revisions.append(
                {
                    "revision_id": f"REV{rev_key:07d}",
                    "bom_header_id": header_id,
                    "part_id": asm["part_id"],
                    "revision_label": rev_label,
                    "effective_from": eff_from,
                    "effective_to": eff_to,
                    "is_current": rev_i == n_revs - 1,
                }
            )
            # last revision carries the component list (earlier revs vary slightly)
            if rev_i == n_revs - 1:
                for child in chosen:
                    comp_key += 1
                    components.append(
                        {
                            "bom_component_id": f"BMC{comp_key:07d}",
                            "bom_header_id": header_id,
                            "parent_part_id": asm["part_id"],
                            "child_part_id": str(child),
                            "quantity_per": float(ctx.choice([1, 1, 1, 2, 2, 3, 4, 6, 8, 10, 12])),
                            "uom": "EA",
                            "revision_label": rev_label,
                            "effective_from": eff_from,
                            "effective_to": None,
                            "position": comp_key % 990 + 10,
                        }
                    )
    return pd.DataFrame(headers), pd.DataFrame(components), pd.DataFrame(revisions)


def generate_ecos(ctx: GenContext, revisions: pd.DataFrame) -> pd.DataFrame:
    n = int(len(revisions) * ctx.cfg.eco_ratio) or 1
    chosen = revisions.sample(
        n=min(n, len(revisions)), random_state=int(ctx.rng.integers(0, 2**31))
    )
    rows = []
    for i, (_, rev) in enumerate(chosen.iterrows(), start=1):
        rows.append(
            {
                "eco_id": f"ECO{i:06d}",
                "part_id": rev["part_id"],
                "revision_id": rev["revision_id"],
                "change_type": str(
                    ctx.choice(["DESIGN_CHANGE", "COST_REDUCTION", "SUPPLIER_CHANGE", "SAFETY"])
                ),
                "status": str(
                    ctx.weighted_keys({"RELEASED": 0.7, "IN_REVIEW": 0.2, "DRAFT": 0.1}, 1)[0]
                ),
                "created_date": rev["effective_from"],
            }
        )
    return pd.DataFrame(rows)


def generate_substitutions(ctx: GenContext, parts: pd.DataFrame) -> pd.DataFrame:
    n = int(len(parts) * ctx.cfg.substitution_ratio) or 1
    rows = []
    for i in range(1, n + 1):
        cat = parts.sample(n=1, random_state=int(ctx.rng.integers(0, 2**31)))["category"].iloc[0]
        same_cat = parts[parts["category"] == cat]
        if len(same_cat) < 2:
            continue
        pair = same_cat.sample(n=2, random_state=int(ctx.rng.integers(0, 2**31)))
        rows.append(
            {
                "substitution_id": f"SUB{i:06d}",
                "part_id": pair.iloc[0]["part_id"],
                "substitute_part_id": pair.iloc[1]["part_id"],
                "substitution_type": str(ctx.choice(["FULL", "CONDITIONAL", "EMERGENCY"])),
                "valid_from": ctx.past_date(max_days=1000),
            }
        )
    return pd.DataFrame(rows)


def generate_supersessions(ctx: GenContext, parts: pd.DataFrame) -> pd.DataFrame:
    obsolete = parts[parts["lifecycle_status"] == "OBSOLETE"]
    active = parts[parts["lifecycle_status"] == "ACTIVE"]
    n = min(int(len(parts) * ctx.cfg.supersession_ratio) or 1, len(obsolete))
    if n == 0 or active.empty:
        return pd.DataFrame(
            columns=["supersession_id", "old_part_id", "new_part_id", "effective_date"]
        )
    old = obsolete.sample(n=n, random_state=int(ctx.rng.integers(0, 2**31)))
    rows = []
    for i, (_, p) in enumerate(old.iterrows(), start=1):
        same_cat = active[active["category"] == p["category"]]
        pool = same_cat if not same_cat.empty else active
        new = pool.sample(n=1, random_state=int(ctx.rng.integers(0, 2**31)))
        rows.append(
            {
                "supersession_id": f"SSN{i:06d}",
                "old_part_id": p["part_id"],
                "new_part_id": new.iloc[0]["part_id"],
                "effective_date": ctx.past_date(max_days=1500),
            }
        )
    return pd.DataFrame(rows)
