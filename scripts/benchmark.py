"""Measure and record platform performance on a chosen profile.

Usage:
    python scripts/benchmark.py [--profile smoke] [--seed 20260716]

Writes evaluation/performance/benchmarks_<profile>.json with stage timings that
were actually measured on this machine (no extrapolation).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    from api.app.dependencies import get_remediation_engine, get_warehouse
    from api.app.main import app
    from data_generator.injectors import inject_all
    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, generate_all, run_generation
    from fastapi.testclient import TestClient

    from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
    from bom_guardian.bom_graph import BomGraph
    from bom_guardian.entity_resolution import WeightedMatcher
    from bom_guardian.impact_twin import ImpactTwin
    from bom_guardian.ingestion import IngestionService
    from bom_guardian.quality import QualityScorer, RuleEngine
    from bom_guardian.testing import TRANSFORM_SQL
    from bom_guardian.warehouse import LocalWarehouse

    timings: dict[str, float] = {}

    def timed(name: str, fn):  # type: ignore[no-untyped-def]
        t0 = time.perf_counter()
        result = fn()
        timings[name] = round(time.perf_counter() - t0, 2)
        return result

    clean = timed("generate_seconds", lambda: generate_all(args.profile, args.seed))
    injected = timed("inject_seconds", lambda: inject_all(clean, seed=args.seed, rate=0.02))
    total_records = sum(len(df) for df in injected.data.values())

    # persist to disk once so ingestion measures real file IO
    timed(
        "write_and_ingest_seconds",
        lambda: _ingest(run_generation, IngestionService, LocalWarehouse, args),
    )

    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(DEFAULT_OUTPUT_ROOT / args.profile, profile=args.profile)
    svc.load_ground_truth(DEFAULT_OUTPUT_ROOT / args.profile / "ground_truth" / "labels.csv")
    for sql in TRANSFORM_SQL:
        wh.execute(sql)

    timed("quality_rules_seconds", lambda: RuleEngine(wh).run_all())
    timed("quality_scoring_seconds", lambda: QualityScorer(wh).run_all())
    timed(
        "entity_resolution_seconds",
        lambda: WeightedMatcher().find_matches(injected.data["part_master"]),
    )

    comps = wh.query(
        "SELECT parent_part_key AS parent_part_id, child_part_key AS child_part_id, "
        "quantity_per, bom_rel_key AS bom_component_id FROM core.fact_bom_relationship"
    )
    twin = ImpactTwin(
        graph=BomGraph.from_components(comps),
        parts=wh.query(
            "SELECT part_key AS part_id, standard_cost, primary_plant, description, "
            "lifecycle_status, uom FROM core.dim_part"
        ),
        inventory=wh.query("SELECT part_key AS part_id, on_hand_value FROM core.fact_inventory"),
        future_demand=wh.query(
            "SELECT part_key AS part_id, demand_qty FROM core.fact_future_demand"
        ),
        po_lines=wh.query("SELECT part_key AS part_id, line_value FROM core.fact_purchase_order"),
        production_orders=wh.query("SELECT part_id, status FROM raw.production_orders"),
        supplier_parts=wh.query("SELECT part_id, supplier_id FROM raw.supplier_parts"),
    )
    sample_parts = comps["child_part_id"].head(25).tolist()
    t0 = time.perf_counter()
    for pid in sample_parts:
        twin.blast_radius(str(pid))
    timings["impact_per_part_ms"] = round(
        (time.perf_counter() - t0) / max(len(sample_parts), 1) * 1000, 1
    )

    app.dependency_overrides[get_warehouse] = lambda: wh
    app.dependency_overrides[get_remediation_engine] = lambda: RemediationEngine(
        DeterministicMockAIProvider(), warehouse=wh
    )
    with TestClient(app) as client:
        for path, key in [
            ("/api/v1/parts?page_size=25", "api_parts_list_ms"),
            ("/api/v1/issues?page_size=25", "api_issues_list_ms"),
            ("/api/v1/analytics/quality", "api_analytics_quality_ms"),
        ]:
            t0 = time.perf_counter()
            for _ in range(5):
                assert client.get(path).status_code == 200
            timings[key] = round((time.perf_counter() - t0) / 5 * 1000, 1)
    app.dependency_overrides.clear()
    wh.close()

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "seed": args.seed,
        "total_records_including_injection": total_records,
        "machine": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
        "note": "All numbers measured on this machine for this profile; nothing extrapolated.",
        "timings": timings,
    }
    out = REPO / "evaluation" / "performance" / f"benchmarks_{args.profile}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Report written to {out}")
    print(json.dumps(timings, indent=2))
    return 0


def _ingest(run_generation, ingestion_service_cls, warehouse_cls, args):  # type: ignore[no-untyped-def]
    run_generation(args.profile, args.seed, inject=True)
    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT

    with warehouse_cls(":memory:") as wh:
        ingestion_service_cls(wh).ingest_directory(
            DEFAULT_OUTPUT_ROOT / args.profile, profile=args.profile
        )


if __name__ == "__main__":
    raise SystemExit(main())
