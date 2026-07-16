"""Master-data generators: parts, aliases, suppliers, plants, warehouses, UOM, categories."""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from data_generator import reference as ref
from data_generator.generators.context import GenContext


def _make_part_number(ctx: GenContext, source_system: str, category: str, num: int) -> str:
    style = ref.PART_NUMBER_STYLES[source_system]
    alpha = "".join(ctx.rng.choice(list("ABCDEFGHJKLMNPQRSTUVWX"), size=2))
    return (
        style.replace("{cat3}", category[:3])
        .replace("{num6}", f"{num:06d}")
        .replace("{alpha2}", alpha)
        .replace("{rev}", str(ctx.rng.choice(list("ABC"))))
    )


def _make_description(ctx: GenContext, category: str) -> str:
    noun = str(ctx.choice(ref.NOUNS))
    parts = [noun]
    if ctx.rng.random() < 0.8:
        parts.insert(0, str(ctx.choice(ref.MODIFIERS)))
    if ctx.rng.random() < 0.7:
        parts.append(str(ctx.choice(ref.SPEC_TOKENS)))
    if ctx.rng.random() < 0.3:
        parts.append(category.replace("_", " ").title())
    return " ".join(parts)


def generate_units_of_measure(ctx: GenContext) -> pd.DataFrame:
    descriptions = {
        "EA": "Each",
        "KG": "Kilogram",
        "G": "Gram",
        "M": "Meter",
        "CM": "Centimeter",
        "MM": "Millimeter",
        "L": "Liter",
        "ML": "Milliliter",
        "M2": "Square meter",
        "SET": "Set",
        "PR": "Pair",
        "ROL": "Roll",
    }
    return pd.DataFrame({"uom_code": ref.UOMS, "description": [descriptions[u] for u in ref.UOMS]})


def generate_product_categories(ctx: GenContext) -> pd.DataFrame:
    rows = [
        {"category_code": c, "category_name": c.replace("_", " ").title(), "bom_tier": v["tier"]}
        for c, v in ref.CATEGORIES.items()
    ]
    return pd.DataFrame(rows)


def generate_plants(ctx: GenContext) -> pd.DataFrame:
    locs = ref.PLANT_LOCATIONS[: ctx.cfg.n_plants]
    return pd.DataFrame(
        [
            {
                "plant_code": f"PL{i + 1:02d}",
                "plant_name": f"{city} Plant",
                "country": country,
                "region": region,
                "currency": dict(ref.COUNTRIES_CURRENCY).get(country, "USD"),
            }
            for i, (city, country, region) in enumerate(locs)
        ]
    )


def generate_warehouses(ctx: GenContext, plants: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = 0
    for _, plant in plants.iterrows():
        for j in range(ctx.cfg.warehouses_per_plant):
            n += 1
            zone = "Central" if j == 0 else f"Satellite {j}"
            rows.append(
                {
                    "warehouse_code": f"WH{n:03d}",
                    "warehouse_name": f"{plant['plant_name']} - {zone}",
                    "plant_code": plant["plant_code"],
                }
            )
    return pd.DataFrame(rows)


def generate_suppliers(ctx: GenContext) -> pd.DataFrame:
    n = ctx.cfg.n_suppliers
    cores = ctx.choice(ref.SUPPLIER_NAME_CORES, size=n)
    suffixes = ctx.choice(ref.SUPPLIER_NAME_SUFFIXES, size=n)
    forms = ctx.choice(ref.SUPPLIER_LEGAL_FORMS, size=n)
    cc = [ref.COUNTRIES_CURRENCY[i] for i in ctx.rng.integers(0, len(ref.COUNTRIES_CURRENCY), n)]
    created = ctx.past_dates(n, max_days=3650, min_days=180)
    source = ctx.weighted_keys({"SAP_ECC": 0.5, "ORACLE_EBS": 0.3, "LEGACY_MFG": 0.2}, n)
    names = [f"{c} {s} {f}" for c, s, f in zip(cores, suffixes, forms, strict=True)]
    return pd.DataFrame(
        {
            "supplier_id": [f"SUP{i + 1:05d}" for i in range(n)],
            "supplier_name": names,
            "country": [c for c, _ in cc],
            "currency": [cur for _, cur in cc],
            "payment_terms": ctx.choice(["NET30", "NET45", "NET60", "NET90"], size=n),
            "source_system": source,
            "status": ctx.weighted_keys({"ACTIVE": 0.9, "BLOCKED": 0.1}, n),
            "created_date": created,
        }
    )


def generate_parts(ctx: GenContext, plants: pd.DataFrame) -> pd.DataFrame:
    n = ctx.cfg.n_parts
    cats = list(ref.CATEGORIES.keys())
    # weight component categories more heavily than finished goods
    weights = np.array(
        [
            4.0
            if ref.CATEGORIES[c]["tier"] == 0
            else 2.0
            if ref.CATEGORIES[c]["tier"] == 1
            else 1.0
            if ref.CATEGORIES[c]["tier"] == 2
            else 0.5
            for c in cats
        ]
    )
    categories = ctx.rng.choice(cats, size=n, p=weights / weights.sum())

    source_systems = ctx.weighted_keys(
        {"SAP_ECC": 0.45, "ORACLE_EBS": 0.25, "LEGACY_MFG": 0.15, "PLM_TEAMCENTER": 0.15}, n
    )
    base_nums = ctx.rng.integers(100000, 999999, size=n)
    statuses = ctx.weighted_keys(ref.LIFECYCLE_STATUSES, n)
    created = ctx.past_dates(n, max_days=3650, min_days=30)

    rows = []
    for i in range(n):
        cat = str(categories[i])
        src = str(source_systems[i])
        cat_info = ref.CATEGORIES[cat]
        price_low, price_high = cat_info["price"]
        # log-uniform gives realistic long-tail pricing
        cost = float(np.exp(ctx.rng.uniform(np.log(price_low), np.log(price_high))))
        proc_type = (
            "MAKE"
            if cat_info["tier"] >= 2 or (cat_info["tier"] == 1 and ctx.rng.random() < 0.5)
            else "BUY"
        )
        upd_lag = int(ctx.rng.integers(0, 720))
        rows.append(
            {
                "part_id": f"PRT{i + 1:06d}",
                "source_part_number": _make_part_number(ctx, src, cat, int(base_nums[i])),
                "source_system": src,
                "description": _make_description(ctx, cat),
                "category": cat,
                "uom": str(ctx.choice(cat_info["uoms"])),
                "lifecycle_status": str(statuses[i]),
                "procurement_type": proc_type,
                "manufacturer_part_number": f"MPN-{ctx.rng.integers(10**7, 10**8):08d}"
                if ctx.rng.random() < 0.75
                else None,
                "standard_cost": round(cost, 4),
                "currency": "USD",
                "lead_time_days": int(ctx.rng.integers(1, 120)),
                "primary_plant": str(ctx.choice(plants["plant_code"].tolist())),
                "bom_tier": cat_info["tier"],
                "created_date": created[i],
                "last_updated": created[i]
                + timedelta(days=min(upd_lag, (ctx.today - created[i]).days)),
            }
        )
    return pd.DataFrame(rows)


def generate_part_aliases(ctx: GenContext, parts: pd.DataFrame) -> pd.DataFrame:
    n_alias = int(len(parts) * ctx.cfg.alias_ratio)
    chosen = parts.sample(n=n_alias, random_state=int(ctx.rng.integers(0, 2**31)))
    rows = []
    for i, (_, p) in enumerate(chosen.iterrows()):
        other_sources = [s for s in ref.PART_NUMBER_STYLES if s != p["source_system"]]
        alias_src = str(ctx.choice(other_sources))
        num = int(ctx.rng.integers(100000, 999999))
        rows.append(
            {
                "alias_id": f"ALS{i + 1:06d}",
                "part_id": p["part_id"],
                "alias_part_number": _make_part_number(ctx, alias_src, p["category"], num),
                "alias_source_system": alias_src,
                "alias_type": str(ctx.choice(["CROSS_REFERENCE", "CUSTOMER_PN", "LEGACY_PN"])),
            }
        )
    return pd.DataFrame(rows)


def generate_supplier_parts(
    ctx: GenContext, parts: pd.DataFrame, suppliers: pd.DataFrame
) -> pd.DataFrame:
    buy_parts = parts[parts["procurement_type"] == "BUY"]
    supplier_ids = suppliers["supplier_id"].tolist()
    # supplier concentration: a minority of suppliers take most relationships
    conc = ctx.rng.pareto(1.5, size=len(supplier_ids)) + 1
    p = conc / conc.sum()
    rows = []
    k = 0
    for _, part in buy_parts.iterrows():
        n_sup = max(1, int(ctx.rng.poisson(ctx.cfg.suppliers_per_part - 1) + 1))
        chosen = set()
        for _ in range(n_sup):
            sup = str(ctx.rng.choice(supplier_ids, p=p))
            if sup in chosen:
                continue
            chosen.add(sup)
            k += 1
            price_factor = float(ctx.rng.uniform(0.85, 1.15))
            rows.append(
                {
                    "supplier_part_id": f"SPR{k:07d}",
                    "supplier_id": sup,
                    "part_id": part["part_id"],
                    "supplier_part_number": f"V{ctx.rng.integers(10**6, 10**7):07d}",
                    "unit_price": round(part["standard_cost"] * price_factor, 4),
                    "currency": part["currency"],
                    "lead_time_days": max(
                        1, int(part["lead_time_days"] + ctx.rng.integers(-10, 15))
                    ),
                    "min_order_qty": int(ctx.choice([1, 10, 25, 50, 100, 500])),
                    "is_primary": len(chosen) == 1,
                }
            )
    return pd.DataFrame(rows)
