"""Operational-data generators: inventory, purchase orders, demand, production
orders, cost history, lead-time history, supplier quotes."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from data_generator.generators.context import GenContext


def generate_inventory(
    ctx: GenContext, parts: pd.DataFrame, warehouses: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    wh_codes = warehouses["warehouse_code"].tolist()
    snapshot_dates = [
        ctx.today - timedelta(days=30 * i) for i in range(ctx.cfg.inventory_snapshots)
    ]
    key = 0
    for _, part in parts.iterrows():
        n_wh = int(ctx.rng.integers(1, min(3, len(wh_codes)) + 1))
        part_whs = ctx.rng.choice(wh_codes, size=n_wh, replace=False)
        for wh in part_whs:
            for snap in snapshot_dates:
                key += 1
                qty = float(max(0, ctx.rng.lognormal(3.0, 1.5)))
                rows.append(
                    {
                        "inventory_id": f"INV{key:08d}",
                        "part_id": part["part_id"],
                        "warehouse_code": str(wh),
                        "snapshot_date": snap,
                        "on_hand_qty": round(qty, 2),
                        "on_hand_value": round(qty * part["standard_cost"], 2),
                        "safety_stock_qty": round(qty * float(ctx.rng.uniform(0.05, 0.3)), 2),
                    }
                )
    return pd.DataFrame(rows)


def generate_purchase_orders(
    ctx: GenContext, supplier_parts: pd.DataFrame, plants: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if supplier_parts.empty:
        return pd.DataFrame(), pd.DataFrame()
    n_lines = int(len(supplier_parts) * ctx.cfg.po_lines_per_part)
    picks = supplier_parts.sample(
        n=n_lines, replace=True, random_state=int(ctx.rng.integers(0, 2**31))
    )
    plant_codes = plants["plant_code"].tolist()

    headers: dict[tuple[str, int], str] = {}
    header_rows, line_rows = [], []
    line_no: dict[str, int] = {}
    for i, (_, sp) in enumerate(picks.iterrows(), start=1):
        bucket = int(ctx.rng.integers(0, 6))  # group lines into POs per supplier
        hkey = (sp["supplier_id"], bucket)
        if hkey not in headers:
            po_id = f"PO{len(headers) + 1:07d}"
            headers[hkey] = po_id
            order_date = ctx.past_date(max_days=365)
            header_rows.append(
                {
                    "po_id": po_id,
                    "supplier_id": sp["supplier_id"],
                    "plant_code": str(ctx.choice(plant_codes)),
                    "order_date": order_date,
                    "currency": sp["currency"],
                    "status": str(
                        ctx.weighted_keys({"OPEN": 0.35, "RECEIVED": 0.55, "CANCELLED": 0.1}, 1)[0]
                    ),
                }
            )
        po_id = headers[hkey]
        line_no[po_id] = line_no.get(po_id, 0) + 1
        qty = int(ctx.choice([10, 25, 50, 100, 250, 500, 1000]))
        line_rows.append(
            {
                "po_line_id": f"POL{i:08d}",
                "po_id": po_id,
                "line_number": line_no[po_id],
                "part_id": sp["part_id"],
                "order_qty": qty,
                "unit_price": sp["unit_price"],
                "line_value": round(qty * sp["unit_price"], 2),
                "promised_date": ctx.today + timedelta(days=int(ctx.rng.integers(-60, 120))),
            }
        )
    return pd.DataFrame(header_rows), pd.DataFrame(line_rows)


def generate_future_demand(
    ctx: GenContext, parts: pd.DataFrame, bom_components: pd.DataFrame, plants: pd.DataFrame
) -> pd.DataFrame:
    """Demand lands on assemblies (independent) and flows implicitly to components.

    Only ACTIVE parts receive demand on the clean baseline, so obsolete/blocked parts
    never organically carry future demand (XFLD-002/003). The injector creates those
    defects deliberately by blocking a part that already has demand.
    """
    active_parts = parts[parts["lifecycle_status"] == "ACTIVE"]
    assemblies = active_parts[
        active_parts["part_id"].isin(bom_components["parent_part_id"].unique())
    ]
    others = active_parts[active_parts["bom_tier"] == 0].sample(
        frac=0.3, random_state=int(ctx.rng.integers(0, 2**31))
    )
    demand_parts = pd.concat([assemblies, others])
    n = int(len(demand_parts) * ctx.cfg.demand_rows_per_part)
    picks = demand_parts.sample(n=n, replace=True, random_state=int(ctx.rng.integers(0, 2**31)))
    plant_codes = plants["plant_code"].tolist()
    dates = ctx.future_dates(len(picks), max_days=270)
    rows = [
        {
            "demand_id": f"DEM{i:07d}",
            "part_id": p["part_id"],
            "plant_code": str(ctx.choice(plant_codes)),
            "demand_date": dates[i - 1],
            "demand_qty": int(ctx.choice([5, 10, 20, 50, 100, 200])),
            "demand_type": str(ctx.weighted_keys({"FORECAST": 0.6, "SALES_ORDER": 0.4}, 1)[0]),
        }
        for i, (_, p) in enumerate(picks.iterrows(), start=1)
    ]
    return pd.DataFrame(rows)


def generate_production_orders(ctx: GenContext, bom_headers: pd.DataFrame) -> pd.DataFrame:
    if bom_headers.empty:
        return pd.DataFrame()
    n = int(len(bom_headers) * ctx.cfg.production_order_ratio) or 1
    picks = bom_headers.sample(n=n, replace=True, random_state=int(ctx.rng.integers(0, 2**31)))
    rows = []
    for i, (_, h) in enumerate(picks.iterrows(), start=1):
        start = ctx.today + timedelta(days=int(ctx.rng.integers(-30, 90)))
        rows.append(
            {
                "production_order_id": f"PRO{i:07d}",
                "part_id": h["parent_part_id"],
                "plant_code": h["plant_code"],
                "order_qty": int(ctx.choice([10, 25, 50, 100])),
                "start_date": start,
                "due_date": start + timedelta(days=int(ctx.rng.integers(5, 45))),
                "status": str(
                    ctx.weighted_keys({"PLANNED": 0.4, "RELEASED": 0.4, "COMPLETED": 0.2}, 1)[0]
                ),
            }
        )
    return pd.DataFrame(rows)


def generate_cost_history(ctx: GenContext, parts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    key = 0
    for _, part in parts.iterrows():
        cost = part["standard_cost"]
        n_hist = ctx.cfg.cost_history_per_part
        for j in range(n_hist, 0, -1):
            key += 1
            # walk the cost backward with modest drift
            factor = float(ctx.rng.uniform(0.93, 1.07)) if j > 1 else 1.0
            cost = round(cost * factor, 4)
            rows.append(
                {
                    "cost_history_id": f"CST{key:08d}",
                    "part_id": part["part_id"],
                    "plant_code": part["primary_plant"],
                    "standard_cost": cost,
                    "currency": part["currency"],
                    "effective_from": ctx.today - timedelta(days=90 * j),
                }
            )
    return pd.DataFrame(rows)


def generate_lead_time_history(ctx: GenContext, supplier_parts: pd.DataFrame) -> pd.DataFrame:
    if supplier_parts.empty:
        return pd.DataFrame()
    rows = []
    key = 0
    n_hist = ctx.cfg.lead_time_history_per_part
    sample = supplier_parts.sample(frac=0.8, random_state=int(ctx.rng.integers(0, 2**31)))
    for _, sp in sample.iterrows():
        lt = sp["lead_time_days"]
        for j in range(n_hist, 0, -1):
            key += 1
            lt = max(1, int(lt + ctx.rng.integers(-7, 8))) if j > 1 else sp["lead_time_days"]
            rows.append(
                {
                    "lead_time_history_id": f"LTH{key:08d}",
                    "part_id": sp["part_id"],
                    "supplier_id": sp["supplier_id"],
                    "lead_time_days": lt,
                    "effective_from": ctx.today - timedelta(days=120 * j),
                }
            )
    return pd.DataFrame(rows)


def generate_supplier_quotes(ctx: GenContext, supplier_parts: pd.DataFrame) -> pd.DataFrame:
    if supplier_parts.empty:
        return pd.DataFrame()
    n = int(len(supplier_parts) * ctx.cfg.quote_ratio) or 1
    picks = supplier_parts.sample(n=n, random_state=int(ctx.rng.integers(0, 2**31)))
    rows = []
    for i, (_, sp) in enumerate(picks.iterrows(), start=1):
        valid_from = ctx.past_date(max_days=365)
        rows.append(
            {
                "quote_id": f"QTE{i:07d}",
                "supplier_id": sp["supplier_id"],
                "part_id": sp["part_id"],
                "quoted_price": round(sp["unit_price"] * float(ctx.rng.uniform(0.9, 1.1)), 4),
                "currency": sp["currency"],
                "quoted_lead_time_days": max(
                    1, int(sp["lead_time_days"] + ctx.rng.integers(-5, 10))
                ),
                "min_order_qty": sp["min_order_qty"],
                "valid_from": valid_from,
                "valid_to": valid_from + timedelta(days=int(ctx.rng.integers(90, 365))),
            }
        )
    return pd.DataFrame(rows)
