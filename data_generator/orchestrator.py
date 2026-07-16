"""Generation orchestrator: runs all generators, validates referential integrity,
writes CSVs plus a manifest with actual record counts."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from bom_guardian.observability import configure_logging, get_logger
from data_generator.config.profiles import PROFILES
from data_generator.generators import bom, masters, operations
from data_generator.generators.context import GenContext

DEFAULT_OUTPUT_ROOT = Path("data_generator/output")


def generate_all(profile: str, seed: int) -> dict[str, pd.DataFrame]:
    """Generate every dataset for a profile. Deterministic for (profile, seed)."""
    cfg = PROFILES[profile]
    ctx = GenContext(cfg=cfg, seed=seed)

    uoms = masters.generate_units_of_measure(ctx)
    categories = masters.generate_product_categories(ctx)
    plants = masters.generate_plants(ctx)
    warehouses = masters.generate_warehouses(ctx, plants)
    suppliers = masters.generate_suppliers(ctx)
    parts = masters.generate_parts(ctx, plants)
    part_aliases = masters.generate_part_aliases(ctx, parts)
    supplier_parts = masters.generate_supplier_parts(ctx, parts, suppliers)

    bom_headers, bom_components, revisions = bom.generate_bom(ctx, parts)
    ecos = bom.generate_ecos(ctx, revisions)
    substitutions = bom.generate_substitutions(ctx, parts)
    supersessions = bom.generate_supersessions(ctx, parts)

    inventory = operations.generate_inventory(ctx, parts, warehouses)
    po_headers, po_lines = operations.generate_purchase_orders(ctx, supplier_parts, plants)
    future_demand = operations.generate_future_demand(ctx, parts, bom_components, plants)
    production_orders = operations.generate_production_orders(ctx, bom_headers)
    cost_history = operations.generate_cost_history(ctx, parts)
    lead_time_history = operations.generate_lead_time_history(ctx, supplier_parts)
    supplier_quotes = operations.generate_supplier_quotes(ctx, supplier_parts)

    return {
        "units_of_measure": uoms,
        "product_categories": categories,
        "plants": plants,
        "warehouses": warehouses,
        "suppliers": suppliers,
        "part_master": parts,
        "part_aliases": part_aliases,
        "supplier_parts": supplier_parts,
        "bom_headers": bom_headers,
        "bom_components": bom_components,
        "engineering_revisions": revisions,
        "engineering_change_orders": ecos,
        "part_substitutions": substitutions,
        "part_supersessions": supersessions,
        "inventory_snapshots": inventory,
        "purchase_orders": po_headers,
        "purchase_order_lines": po_lines,
        "future_demand": future_demand,
        "production_orders": production_orders,
        "standard_cost_history": cost_history,
        "lead_time_history": lead_time_history,
        "supplier_quotes": supplier_quotes,
    }


def validate_referential_integrity(data: dict[str, pd.DataFrame]) -> list[str]:
    """Check FK relationships on the clean baseline. Returns list of violations."""
    errors: list[str] = []
    part_ids = set(data["part_master"]["part_id"])
    supplier_ids = set(data["suppliers"]["supplier_id"])
    plant_codes = set(data["plants"]["plant_code"])
    warehouse_codes = set(data["warehouses"]["warehouse_code"])
    uom_codes = set(data["units_of_measure"]["uom_code"])

    def check(df_name: str, column: str, valid: set) -> None:
        df = data[df_name]
        if df.empty or column not in df.columns:
            return
        bad = df[~df[column].isin(valid)][column]
        if not bad.empty:
            errors.append(f"{df_name}.{column}: {len(bad)} orphan values (e.g. {bad.iloc[0]})")

    check("part_master", "uom", uom_codes)
    check("part_master", "primary_plant", plant_codes)
    check("part_aliases", "part_id", part_ids)
    check("supplier_parts", "part_id", part_ids)
    check("supplier_parts", "supplier_id", supplier_ids)
    check("bom_components", "parent_part_id", part_ids)
    check("bom_components", "child_part_id", part_ids)
    check("bom_headers", "parent_part_id", part_ids)
    check("bom_headers", "plant_code", plant_codes)
    check("engineering_revisions", "part_id", part_ids)
    check("part_substitutions", "part_id", part_ids)
    check("part_substitutions", "substitute_part_id", part_ids)
    check("part_supersessions", "old_part_id", part_ids)
    check("part_supersessions", "new_part_id", part_ids)
    check("inventory_snapshots", "part_id", part_ids)
    check("inventory_snapshots", "warehouse_code", warehouse_codes)
    check("purchase_orders", "supplier_id", supplier_ids)
    check("purchase_orders", "plant_code", plant_codes)
    check("purchase_order_lines", "part_id", part_ids)
    check("future_demand", "part_id", part_ids)
    check("future_demand", "plant_code", plant_codes)
    check("production_orders", "part_id", part_ids)
    check("standard_cost_history", "part_id", part_ids)
    check("lead_time_history", "part_id", part_ids)
    check("lead_time_history", "supplier_id", supplier_ids)
    check("supplier_quotes", "part_id", part_ids)
    check("supplier_quotes", "supplier_id", supplier_ids)

    # BOM acyclicity of the clean baseline (tier construction should guarantee it)
    comps = data["bom_components"]
    if not comps.empty:
        import networkx as nx

        g = nx.DiGraph()
        g.add_edges_from(comps[["parent_part_id", "child_part_id"]].itertuples(index=False))
        if not nx.is_directed_acyclic_graph(g):
            errors.append("bom_components: baseline BOM graph contains cycles")
    return errors


def run_generation(
    profile: str,
    seed: int,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    inject: bool = False,
    inject_rate: float = 0.02,
) -> dict:
    """Generate, validate, optionally inject defects, write CSVs + manifest.

    With inject=True, the written datasets contain controlled defects and the
    hidden labels go to <profile>/ground_truth/ — separate from model inputs.
    """
    configure_logging()
    log = get_logger("data_generator", profile=profile, seed=seed)
    started = time.perf_counter()

    data = generate_all(profile, seed)
    errors = validate_referential_integrity(data)
    if errors:
        for e in errors:
            log.error("referential_integrity_violation", detail=e)
        raise ValueError(f"Referential integrity violations: {errors}")

    injection_summary: dict | None = None
    if inject:
        from data_generator.injectors import inject_all

        result = inject_all(data, seed=seed, rate=inject_rate)
        data = result.data
        gt_dir = output_root / profile / "ground_truth"
        gt_dir.mkdir(parents=True, exist_ok=True)
        result.ground_truth.to_csv(gt_dir / "labels.csv", index=False)
        injection_summary = {
            "total_injections": len(result.ground_truth),
            "rate": inject_rate,
            "issue_types": result.counts_by_type,
            "labels_file": "ground_truth/labels.csv",
        }
        (gt_dir / "injection_manifest.json").write_text(json.dumps(injection_summary, indent=2))
        log.info("injection_complete", total=len(result.ground_truth))

    out_dir = output_root / profile
    out_dir.mkdir(parents=True, exist_ok=True)
    datasets = {}
    total = 0
    for name, df in data.items():
        path = out_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        datasets[name] = {"records": len(df), "file": path.name, "sha256": sha}
        total += len(df)
        log.info("dataset_written", dataset=name, records=len(df))

    manifest = {
        "profile": profile,
        "seed": seed,
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round(time.perf_counter() - started, 2),
        "total_records": total,
        "datasets": datasets,
        "referential_integrity": "validated_before_injection" if inject else "validated",
        "injection": injection_summary,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log.info("generation_complete", total_records=total)
    return manifest
