"""Golden-record survivorship tests: field-level mixing, lineage, reversibility."""

from datetime import date

import pandas as pd
import pytest

from bom_guardian.golden_record import GoldenRecordBuilder


def _cluster() -> pd.DataFrame:
    """Three source records for the same physical part with divergent fields."""
    return pd.DataFrame(
        [
            {  # ERP: reliable ids/cost, older description
                "part_id": "PRT-ERP",
                "source_system": "SAP_ECC",
                "source_part_number": "FAS-100200",
                "description": "BOLT",
                "category": "FASTENERS",
                "uom": "EA",
                "lifecycle_status": "ACTIVE",
                "manufacturer_part_number": "MPN-11110000",
                "standard_cost": 1.10,
                "lead_time_days": 14,
                "primary_plant": "PL01",
                "last_updated": date(2026, 5, 1),
            },
            {  # PLM: rich engineering description, no cost
                "part_id": "PRT-PLM",
                "source_system": "PLM_TEAMCENTER",
                "source_part_number": "FAS-100200-A",
                "description": "STAINLESS BOLT M3X8 PRECISION",
                "category": "FASTENERS",
                "uom": "EA",
                "lifecycle_status": "ACTIVE",
                "manufacturer_part_number": "MPN-11110000",
                "standard_cost": None,
                "lead_time_days": None,
                "primary_plant": "PL01",
                "last_updated": date(2026, 6, 20),
            },
            {  # Supplier portal: fresh lead time, weak identifiers
                "part_id": "PRT-SUP",
                "source_system": "SUPPLIER_PORTAL",
                "source_part_number": "QX-100200",
                "description": "bolt m3x8",
                "category": None,
                "uom": "EA",
                "lifecycle_status": "ACTIVE",
                "manufacturer_part_number": None,
                "standard_cost": 1.45,
                "lead_time_days": 9,
                "primary_plant": None,
                "last_updated": date(2026, 6, 28),
            },
        ]
    )


@pytest.fixture()
def golden():  # type: ignore[no-untyped-def]
    return GoldenRecordBuilder().build(_cluster(), entity_id="GLD-TEST")


def test_field_level_mixing_across_sources(golden) -> None:  # type: ignore[no-untyped-def]
    """The golden record must combine fields from different source rows."""
    sources_used = {d.source_record for d in golden.fields.values()}
    assert len(sources_used) >= 2, f"expected field-level mixing, got {sources_used}"


def test_domain_preferences_apply(golden) -> None:  # type: ignore[no-untyped-def]
    assert golden.fields["description"].source_system == "PLM_TEAMCENTER"
    assert golden.fields["standard_cost"].source_system == "SAP_ECC"
    assert golden.fields["lead_time_days"].source_system == "SUPPLIER_PORTAL"


def test_every_decision_has_full_lineage(golden) -> None:  # type: ignore[no-untyped-def]
    for name, d in golden.fields.items():
        assert d.source_record, name
        assert d.source_system, name
        assert d.reason, name
        assert 0.0 <= d.confidence <= 1.0, name
        assert d.selected_at, name
        assert d.version == "1.0"


def test_alternatives_enable_reversibility(golden) -> None:  # type: ignore[no-untyped-def]
    desc = golden.fields["description"]
    alt_values = {str(a.value) for a in desc.alternatives}
    assert "BOLT" in alt_values or "bolt m3x8" in alt_values
    for alt in desc.alternatives:
        assert alt.source_record  # every alternative traceable to its source


def test_agreement_boosts_common_values(golden) -> None:  # type: ignore[no-untyped-def]
    uom = golden.fields["uom"]
    assert uom.selected_value == "EA"
    assert "cross_source_agreement" in uom.reason


def test_missing_everywhere_field_is_skipped() -> None:
    cluster = _cluster()
    cluster["category"] = None
    golden = GoldenRecordBuilder().build(cluster)
    assert "category" not in golden.fields


def test_empty_cluster_rejected() -> None:
    with pytest.raises(ValueError):
        GoldenRecordBuilder().build(pd.DataFrame())


def test_deterministic(golden) -> None:  # type: ignore[no-untyped-def]
    again = GoldenRecordBuilder().build(_cluster(), entity_id="GLD-TEST")
    assert golden.as_flat_dict() == again.as_flat_dict()


def test_members_recorded(golden) -> None:  # type: ignore[no-untyped-def]
    assert set(golden.member_record_ids) == {"PRT-ERP", "PRT-PLM", "PRT-SUP"}
