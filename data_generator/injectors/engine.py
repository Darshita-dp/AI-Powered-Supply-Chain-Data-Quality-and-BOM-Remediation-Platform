"""Issue-injection engine.

Takes the clean generated datasets, injects 25 controlled defect types, and
returns corrupted datasets plus a ground-truth label for every injection.
Ground truth is written to a separate directory and must never be joined into
model inputs (ADR-004); it exists only for evaluation.

Every injector follows the same contract:
    def _inject_x(data, ctx) -> list[GroundTruthLabel-like dict]
mutating `data` in place and returning its labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass
class InjectCtx:
    rng: np.random.Generator
    seed: int
    rate: float  # base fraction of eligible records to corrupt per issue type
    today: date = date(2026, 7, 1)
    labels: list[dict] = field(default_factory=list)
    _counter: int = 0

    def new_id(self) -> str:
        self._counter += 1
        return f"INJ{self._counter:06d}"

    def label(
        self,
        issue_type: str,
        dataset: str,
        record_id: str,
        difficulty: str,
        field_name: str | None = None,
        original_value=None,
        injected_value=None,
        correct_value=None,
        correct_matching_entity: str | None = None,
    ) -> None:
        self.labels.append(
            {
                "injection_id": self.new_id(),
                "issue_type": issue_type,
                "dataset": dataset,
                "record_id": record_id,
                "field": field_name,
                "original_value": None if original_value is None else str(original_value),
                "injected_value": None if injected_value is None else str(injected_value),
                "correct_value": None if correct_value is None else str(correct_value),
                "correct_matching_entity": correct_matching_entity,
                "difficulty": difficulty,
                "seed": self.seed,
                "injected_at": self.today.isoformat(),
            }
        )

    def pick(self, df: pd.DataFrame, min_n: int = 1, factor: float = 1.0) -> pd.DataFrame:
        n = max(min_n, int(len(df) * self.rate * factor))
        n = min(n, len(df))
        if n == 0:
            return df.head(0)
        idx = self.rng.choice(df.index.to_numpy(), size=n, replace=False)
        return df.loc[idx]

    def difficulty(self) -> str:
        return str(self.rng.choice(["easy", "medium", "hard"], p=[0.4, 0.4, 0.2]))


# --------------------------------------------------------------------------
# Duplicate / conflict injectors
# --------------------------------------------------------------------------


def _perturb_text(ctx: InjectCtx, text: str, level: str) -> str:
    """Realistic entry-noise: casing, punctuation, abbreviation, typos."""
    out = text
    if level == "easy":  # trivial formatting difference
        out = out.lower() if ctx.rng.random() < 0.5 else f" {out} "
    elif level == "medium":
        out = out.replace("-", " ").replace("STAINLESS", "SS").replace("ALUMINUM", "ALUM")
        if ctx.rng.random() < 0.5:
            out = out.title()
    else:  # hard: typo + reorder
        words = out.split()
        if len(words) > 2:
            i, j = ctx.rng.choice(len(words), size=2, replace=False)
            words[int(i)], words[int(j)] = words[int(j)], words[int(i)]
        out = " ".join(words)
        if len(out) > 4:
            k = int(ctx.rng.integers(1, len(out) - 2))
            out = out[:k] + out[k + 1 :]  # drop a character
    return out


def _inject_exact_duplicate_parts(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    chosen = ctx.pick(parts, factor=0.8)
    new_rows = []
    start = len(parts)
    for i, (_, p) in enumerate(chosen.iterrows(), start=1):
        dup = p.copy()
        dup["part_id"] = f"PRT9{start + i:05d}"
        # same part number re-keyed in another source system: exact content duplicate
        other = "ORACLE_EBS" if p["source_system"] != "ORACLE_EBS" else "SAP_ECC"
        dup["source_system"] = other
        new_rows.append(dup)
        ctx.label(
            "exact_duplicate_part",
            "part_master",
            dup["part_id"],
            "easy",
            correct_matching_entity=p["part_id"],
        )
    if new_rows:
        data["part_master"] = pd.concat([parts, pd.DataFrame(new_rows)], ignore_index=True)


def _inject_fuzzy_duplicate_parts(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    chosen = ctx.pick(parts, factor=1.2)
    new_rows = []
    start = len(parts)
    for i, (_, p) in enumerate(chosen.iterrows(), start=1):
        diff = ctx.difficulty()
        dup = p.copy()
        dup["part_id"] = f"PRT8{start + i:05d}"
        dup["description"] = _perturb_text(ctx, p["description"], diff)
        pn = str(p["source_part_number"])
        if diff == "easy":
            dup["source_part_number"] = pn.replace("-", "")
        elif diff == "medium":
            dup["source_part_number"] = f"{pn}-R"
            dup["standard_cost"] = round(p["standard_cost"] * float(ctx.rng.uniform(0.97, 1.03)), 4)
        else:
            dup["source_part_number"] = f"X{pn[1:]}" if len(pn) > 1 else f"X{pn}"
            dup["standard_cost"] = round(p["standard_cost"] * float(ctx.rng.uniform(0.9, 1.1)), 4)
            dup["manufacturer_part_number"] = None
        dup["source_system"] = "LEGACY_MFG"
        new_rows.append(dup)
        ctx.label(
            "fuzzy_duplicate_part",
            "part_master",
            dup["part_id"],
            diff,
            correct_matching_entity=p["part_id"],
        )
    if new_rows:
        data["part_master"] = pd.concat([parts, pd.DataFrame(new_rows)], ignore_index=True)


def _inject_duplicate_suppliers(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    sup = data["suppliers"]
    chosen = ctx.pick(sup, factor=0.8)
    new_rows = []
    start = len(sup)
    for i, (_, s) in enumerate(chosen.iterrows(), start=1):
        diff = ctx.difficulty()
        dup = s.copy()
        dup["supplier_id"] = f"SUP9{start + i:04d}"
        name = str(s["supplier_name"])
        if diff == "easy":
            dup["supplier_name"] = name.upper()
        elif diff == "medium":
            dup["supplier_name"] = (
                name.replace("Inc", "Incorporated")
                .replace("Corp", "Corporation")
                .replace("Manufacturing", "Mfg")
            )
        else:
            dup["supplier_name"] = _perturb_text(ctx, name, "hard")
            dup["country"] = s["country"]  # same country, harder to spot by name alone
        dup["source_system"] = "LEGACY_MFG"
        new_rows.append(dup)
        ctx.label(
            "duplicate_supplier",
            "suppliers",
            dup["supplier_id"],
            diff,
            correct_matching_entity=s["supplier_id"],
        )
    if new_rows:
        data["suppliers"] = pd.concat([sup, pd.DataFrame(new_rows)], ignore_index=True)


def _inject_conflicting_descriptions(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    aliases = data["part_aliases"]
    parts = data["part_master"].set_index("part_id")
    chosen = ctx.pick(aliases)
    for idx, row in chosen.iterrows():
        if row["part_id"] not in parts.index:
            continue
        orig = parts.loc[row["part_id"], "description"]
        conflicted = _perturb_text(ctx, str(orig), "hard") + " ALT"
        data["part_aliases"].loc[idx, "alias_type"] = "CONFLICTING_DESC:" + conflicted
        ctx.label(
            "conflicting_part_descriptions",
            "part_aliases",
            str(row["alias_id"]),
            ctx.difficulty(),
            field_name="description",
            original_value=orig,
            injected_value=conflicted,
            correct_value=orig,
        )


def _inject_conflicting_mpn(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    with_mpn = parts[parts["manufacturer_part_number"].notna()]
    chosen = ctx.pick(with_mpn)
    for idx, row in chosen.iterrows():
        orig = row["manufacturer_part_number"]
        wrong = f"MPN-{ctx.rng.integers(10**7, 10**8):08d}"
        data["part_master"].loc[idx, "manufacturer_part_number"] = wrong
        ctx.label(
            "conflicting_mpn",
            "part_master",
            str(row["part_id"]),
            ctx.difficulty(),
            field_name="manufacturer_part_number",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


# --------------------------------------------------------------------------
# Attribute injectors
# --------------------------------------------------------------------------


def _null_field(
    data: dict[str, pd.DataFrame],
    ctx: InjectCtx,
    issue: str,
    dataset: str,
    id_col: str,
    field_name: str,
    factor: float = 1.0,
) -> None:
    df = data[dataset]
    eligible = df[df[field_name].notna()]
    chosen = ctx.pick(eligible, factor=factor)
    for idx, row in chosen.iterrows():
        orig = row[field_name]
        data[dataset].loc[idx, field_name] = None
        ctx.label(
            issue,
            dataset,
            str(row[id_col]),
            "easy",
            field_name=field_name,
            original_value=orig,
            injected_value=None,
            correct_value=orig,
        )


def _inject_missing_critical_attributes(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    for f in ["description", "uom", "lead_time_days", "standard_cost", "category"]:
        _null_field(
            data, ctx, "missing_critical_attributes", "part_master", "part_id", f, factor=0.4
        )


def _inject_invalid_uom(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    chosen = ctx.pick(parts[parts["uom"].notna()])
    bad_uoms = ["EACH", "PCS", "UNIT", "KGS", "XX", "??"]
    for idx, row in chosen.iterrows():
        orig = row["uom"]
        wrong = str(ctx.rng.choice(bad_uoms))
        data["part_master"].loc[idx, "uom"] = wrong
        ctx.label(
            "invalid_uom",
            "part_master",
            str(row["part_id"]),
            "easy",
            field_name="uom",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


def _inject_zero_and_negative_quantities(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    comps = data["bom_components"]
    zero = ctx.pick(comps, factor=0.5)
    for idx, row in zero.iterrows():
        orig = row["quantity_per"]
        data["bom_components"].loc[idx, "quantity_per"] = 0.0
        ctx.label(
            "zero_component_quantity",
            "bom_components",
            str(row["bom_component_id"]),
            "easy",
            field_name="quantity_per",
            original_value=orig,
            injected_value=0.0,
            correct_value=orig,
        )
    remaining = comps.drop(index=zero.index, errors="ignore")
    neg = ctx.pick(remaining, factor=0.5)
    for idx, row in neg.iterrows():
        orig = row["quantity_per"]
        data["bom_components"].loc[idx, "quantity_per"] = -abs(float(orig))
        ctx.label(
            "negative_component_quantity",
            "bom_components",
            str(row["bom_component_id"]),
            "easy",
            field_name="quantity_per",
            original_value=orig,
            injected_value=-abs(float(orig)),
            correct_value=orig,
        )


def _inject_extreme_cost_changes(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    hist = data["standard_cost_history"]
    latest = hist.sort_values("effective_from").groupby("part_id").tail(1)
    chosen = ctx.pick(latest)
    for idx, row in chosen.iterrows():
        orig = row["standard_cost"]
        factor = float(ctx.rng.choice([0.01, 0.1, 12.0, 100.0]))
        wrong = round(float(orig) * factor, 4)
        data["standard_cost_history"].loc[idx, "standard_cost"] = wrong
        ctx.label(
            "extreme_cost_change",
            "standard_cost_history",
            str(row["cost_history_id"]),
            "medium",
            field_name="standard_cost",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


def _inject_extreme_lead_time_changes(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    hist = data["lead_time_history"]
    latest = hist.sort_values("effective_from").groupby("part_id").tail(1)
    chosen = ctx.pick(latest)
    for idx, row in chosen.iterrows():
        orig = row["lead_time_days"]
        wrong = int(orig) * int(ctx.rng.choice([10, 20])) + 100
        data["lead_time_history"].loc[idx, "lead_time_days"] = wrong
        ctx.label(
            "extreme_lead_time_change",
            "lead_time_history",
            str(row["lead_time_history_id"]),
            "medium",
            field_name="lead_time_days",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


def _inject_supplier_price_conflicts(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    sp = data["supplier_parts"]
    multi = sp[sp.duplicated("part_id", keep=False)]
    chosen = ctx.pick(multi) if not multi.empty else multi
    for idx, row in chosen.iterrows():
        orig = row["unit_price"]
        wrong = round(float(orig) * float(ctx.rng.uniform(3.0, 8.0)), 4)
        data["supplier_parts"].loc[idx, "unit_price"] = wrong
        ctx.label(
            "supplier_price_conflict",
            "supplier_parts",
            str(row["supplier_part_id"]),
            "medium",
            field_name="unit_price",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


def _inject_currency_inconsistencies(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    sp = data["supplier_parts"]
    chosen = ctx.pick(sp)
    for idx, row in chosen.iterrows():
        orig = row["currency"]
        wrong = "JPY" if orig != "JPY" else "USD"
        data["supplier_parts"].loc[idx, "currency"] = wrong
        ctx.label(
            "currency_inconsistency",
            "supplier_parts",
            str(row["supplier_part_id"]),
            "easy",
            field_name="currency",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


def _inject_stale_records(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    active = parts[parts["lifecycle_status"] == "ACTIVE"]
    chosen = ctx.pick(active)
    stale_date = ctx.today - timedelta(days=int(ctx.rng.integers(1500, 3000)))
    for idx, row in chosen.iterrows():
        orig = row["last_updated"]
        data["part_master"].loc[idx, "last_updated"] = stale_date
        ctx.label(
            "stale_record",
            "part_master",
            str(row["part_id"]),
            "easy",
            field_name="last_updated",
            original_value=orig,
            injected_value=stale_date,
            correct_value=orig,
        )


# --------------------------------------------------------------------------
# Structural / graph injectors
# --------------------------------------------------------------------------


def _inject_orphan_bom_components(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    comps = data["bom_components"]
    chosen = ctx.pick(comps, factor=0.5)
    for idx, row in chosen.iterrows():
        orig = row["child_part_id"]
        ghost = f"PRT7{ctx.rng.integers(10**5, 10**6):06d}"
        data["bom_components"].loc[idx, "child_part_id"] = ghost
        ctx.label(
            "orphan_bom_component",
            "bom_components",
            str(row["bom_component_id"]),
            "easy",
            field_name="child_part_id",
            original_value=orig,
            injected_value=ghost,
            correct_value=orig,
        )


def _inject_orphan_bom_parents(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    comps = data["bom_components"]
    chosen = ctx.pick(comps, factor=0.3)
    for idx, row in chosen.iterrows():
        orig = row["parent_part_id"]
        ghost = f"PRT6{ctx.rng.integers(10**5, 10**6):06d}"
        data["bom_components"].loc[idx, "parent_part_id"] = ghost
        ctx.label(
            "orphan_bom_parent",
            "bom_components",
            str(row["bom_component_id"]),
            "easy",
            field_name="parent_part_id",
            original_value=orig,
            injected_value=ghost,
            correct_value=orig,
        )


def _inject_circular_boms(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    """Add a back-edge child->ancestor to create 2- and 3-node cycles."""
    comps = data["bom_components"]
    parents = comps["parent_part_id"].unique()
    n = max(1, int(len(parents) * ctx.rate))
    chosen_parents = ctx.rng.choice(parents, size=min(n, len(parents)), replace=False)
    next_key = len(comps) + 1
    new_rows = []
    for parent in chosen_parents:
        children = comps.loc[comps["parent_part_id"] == parent, "child_part_id"]
        if children.empty:
            continue
        child = str(ctx.rng.choice(children.to_numpy()))
        rec_id = f"BMC9{next_key:06d}"
        next_key += 1
        new_rows.append(
            {
                "bom_component_id": rec_id,
                "bom_header_id": None,
                "parent_part_id": child,  # back-edge: child now "contains" its parent
                "child_part_id": parent,
                "quantity_per": 1.0,
                "uom": "EA",
                "revision_label": "A",
                "effective_from": ctx.today,
                "effective_to": None,
                "position": 999,
            }
        )
        ctx.label(
            "circular_bom",
            "bom_components",
            rec_id,
            "medium",
            field_name="parent_part_id->child_part_id",
            injected_value=f"{child}->{parent}",
        )
    if new_rows:
        data["bom_components"] = pd.concat([comps, pd.DataFrame(new_rows)], ignore_index=True)


def _inject_self_referencing_boms(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    comps = data["bom_components"]
    chosen = ctx.pick(comps, factor=0.2)
    for idx, row in chosen.iterrows():
        orig = row["child_part_id"]
        data["bom_components"].loc[idx, "child_part_id"] = row["parent_part_id"]
        ctx.label(
            "self_referencing_bom",
            "bom_components",
            str(row["bom_component_id"]),
            "easy",
            field_name="child_part_id",
            original_value=orig,
            injected_value=row["parent_part_id"],
            correct_value=orig,
        )


def _inject_overlapping_effective_dates(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    revs = data["engineering_revisions"]
    multi = revs[revs.duplicated("bom_header_id", keep=False)]
    if multi.empty:
        return
    chosen_headers = ctx.rng.choice(
        multi["bom_header_id"].unique(),
        size=max(1, int(multi["bom_header_id"].nunique() * ctx.rate)),
        replace=False,
    )
    for header in chosen_headers:
        rows = revs[revs["bom_header_id"] == header].sort_values("effective_from")
        if len(rows) < 2:
            continue
        first_idx = rows.index[0]
        orig = revs.loc[first_idx, "effective_to"]
        overlap_end = rows.iloc[1]["effective_from"] + timedelta(days=45)
        data["engineering_revisions"].loc[first_idx, "effective_to"] = overlap_end
        ctx.label(
            "overlapping_effective_dates",
            "engineering_revisions",
            str(revs.loc[first_idx, "revision_id"]),
            "medium",
            field_name="effective_to",
            original_value=orig,
            injected_value=overlap_end,
            correct_value=orig,
        )


def _inject_multiple_active_revisions(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    revs = data["engineering_revisions"]
    inactive = revs[~revs["is_current"]]
    chosen = ctx.pick(inactive, factor=0.5) if not inactive.empty else inactive
    for idx, row in chosen.iterrows():
        data["engineering_revisions"].loc[idx, "is_current"] = True
        ctx.label(
            "multiple_active_revisions",
            "engineering_revisions",
            str(row["revision_id"]),
            "medium",
            field_name="is_current",
            original_value=False,
            injected_value=True,
            correct_value=False,
        )


def _inject_obsolete_components_in_active_boms(
    data: dict[str, pd.DataFrame], ctx: InjectCtx
) -> None:
    parts = data["part_master"]
    comps = data["bom_components"]
    obsolete_ids = set(parts.loc[parts["lifecycle_status"] == "OBSOLETE", "part_id"])
    active_children = comps[~comps["child_part_id"].isin(obsolete_ids)]
    chosen = ctx.pick(active_children, factor=0.5)
    parts_by_id = parts.set_index("part_id")
    for _idx, row in chosen.iterrows():
        child = row["child_part_id"]
        if child not in parts_by_id.index:
            continue
        pos = parts.index[parts["part_id"] == child]
        orig = parts_by_id.loc[child, "lifecycle_status"]
        if isinstance(orig, pd.Series):
            orig = orig.iloc[0]
        data["part_master"].loc[pos, "lifecycle_status"] = "OBSOLETE"
        ctx.label(
            "obsolete_component_in_active_bom",
            "bom_components",
            str(row["bom_component_id"]),
            "medium",
            field_name="child_lifecycle_status",
            original_value=orig,
            injected_value="OBSOLETE",
            correct_value=orig,
        )


def _inject_blocked_parts_with_future_demand(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    demand_ids = set(data["future_demand"]["part_id"])
    demanded = parts[parts["part_id"].isin(demand_ids) & (parts["lifecycle_status"] == "ACTIVE")]
    chosen = ctx.pick(demanded, factor=0.5)
    for idx, row in chosen.iterrows():
        data["part_master"].loc[idx, "lifecycle_status"] = "BLOCKED"
        ctx.label(
            "blocked_part_with_future_demand",
            "part_master",
            str(row["part_id"]),
            "medium",
            field_name="lifecycle_status",
            original_value="ACTIVE",
            injected_value="BLOCKED",
            correct_value="ACTIVE",
        )


def _inject_invalid_plant_relationships(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    parts = data["part_master"]
    chosen = ctx.pick(parts, factor=0.5)
    for idx, row in chosen.iterrows():
        orig = row["primary_plant"]
        ghost = f"PL{ctx.rng.integers(80, 99)}"
        data["part_master"].loc[idx, "primary_plant"] = ghost
        ctx.label(
            "invalid_plant_relationship",
            "part_master",
            str(row["part_id"]),
            "easy",
            field_name="primary_plant",
            original_value=orig,
            injected_value=ghost,
            correct_value=orig,
        )


def _inject_invalid_supplier_relationships(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    sp = data["supplier_parts"]
    chosen = ctx.pick(sp, factor=0.5)
    for idx, row in chosen.iterrows():
        orig = row["supplier_id"]
        ghost = f"SUP7{ctx.rng.integers(10**4, 10**5):05d}"
        data["supplier_parts"].loc[idx, "supplier_id"] = ghost
        ctx.label(
            "invalid_supplier_relationship",
            "supplier_parts",
            str(row["supplier_part_id"]),
            "easy",
            field_name="supplier_id",
            original_value=orig,
            injected_value=ghost,
            correct_value=orig,
        )


def _inject_doc_vs_erp_discrepancies(data: dict[str, pd.DataFrame], ctx: InjectCtx) -> None:
    """Make supplier quotes disagree materially with the ERP supplier-part record."""
    quotes = data["supplier_quotes"]
    chosen = ctx.pick(quotes)
    for idx, row in chosen.iterrows():
        orig = row["quoted_price"]
        wrong = round(float(orig) * float(ctx.rng.uniform(1.5, 4.0)), 4)
        data["supplier_quotes"].loc[idx, "quoted_price"] = wrong
        ctx.label(
            "supplier_doc_vs_erp_discrepancy",
            "supplier_quotes",
            str(row["quote_id"]),
            "medium",
            field_name="quoted_price",
            original_value=orig,
            injected_value=wrong,
            correct_value=orig,
        )


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

_INJECTORS = [
    _inject_exact_duplicate_parts,
    _inject_fuzzy_duplicate_parts,
    _inject_duplicate_suppliers,
    _inject_conflicting_descriptions,
    _inject_missing_critical_attributes,
    _inject_invalid_uom,
    _inject_orphan_bom_components,
    _inject_orphan_bom_parents,
    _inject_circular_boms,
    _inject_self_referencing_boms,
    _inject_zero_and_negative_quantities,
    _inject_overlapping_effective_dates,
    _inject_multiple_active_revisions,
    _inject_obsolete_components_in_active_boms,
    _inject_blocked_parts_with_future_demand,
    _inject_extreme_cost_changes,
    _inject_extreme_lead_time_changes,
    _inject_supplier_price_conflicts,
    _inject_currency_inconsistencies,
    _inject_stale_records,
    _inject_invalid_plant_relationships,
    _inject_invalid_supplier_relationships,
    _inject_doc_vs_erp_discrepancies,
    _inject_conflicting_mpn,
]

ISSUE_TYPES: list[str] = [
    "exact_duplicate_part",
    "fuzzy_duplicate_part",
    "duplicate_supplier",
    "conflicting_part_descriptions",
    "missing_critical_attributes",
    "invalid_uom",
    "orphan_bom_component",
    "orphan_bom_parent",
    "circular_bom",
    "self_referencing_bom",
    "zero_component_quantity",
    "negative_component_quantity",
    "overlapping_effective_dates",
    "multiple_active_revisions",
    "obsolete_component_in_active_bom",
    "blocked_part_with_future_demand",
    "extreme_cost_change",
    "extreme_lead_time_change",
    "supplier_price_conflict",
    "currency_inconsistency",
    "stale_record",
    "invalid_plant_relationship",
    "invalid_supplier_relationship",
    "supplier_doc_vs_erp_discrepancy",
    "conflicting_mpn",
]


@dataclass
class InjectionResult:
    data: dict[str, pd.DataFrame]
    ground_truth: pd.DataFrame

    @property
    def counts_by_type(self) -> dict[str, int]:
        return self.ground_truth["issue_type"].value_counts().to_dict()


def inject_all(clean: dict[str, pd.DataFrame], seed: int, rate: float = 0.02) -> InjectionResult:
    """Inject all 25 issue types into copies of the clean datasets.

    `rate` is the base corruption fraction per issue type (some injectors scale it).
    The returned ground truth must be stored separately from model inputs.
    """
    data = {name: df.copy() for name, df in clean.items()}
    ctx = InjectCtx(rng=np.random.default_rng(seed + 1), seed=seed, rate=rate)
    for injector in _INJECTORS:
        injector(data, ctx)
    return InjectionResult(data=data, ground_truth=pd.DataFrame(ctx.labels))
