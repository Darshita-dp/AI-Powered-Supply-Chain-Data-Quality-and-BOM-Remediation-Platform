"""Document intelligence tests: PDF generation, extraction accuracy, injection
controls, and ERP comparison."""

import pandas as pd
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.documents import generate_quote_pdfs
from data_generator.orchestrator import generate_all

from bom_guardian.document_intelligence import QuoteExtractor, compare_with_erp

TINY = ProfileConfig(name="tiny", n_parts=200, n_suppliers=20, n_plants=2, warehouses_per_plant=1)


@pytest.fixture(scope="module")
def setup(tmp_path_factory):  # type: ignore[no-untyped-def]
    PROFILES["tiny"] = TINY
    data = generate_all("tiny", seed=41)
    out = tmp_path_factory.mktemp("docs")
    manifest = generate_quote_pdfs(
        data["supplier_quotes"],
        data["suppliers"],
        out,
        max_docs=12,
        injection_fraction=0.4,
        seed=41,
    )
    return data, out, manifest


@pytest.mark.integration
def test_pdfs_generated(setup) -> None:  # type: ignore[no-untyped-def]
    _, out, manifest = setup
    assert len(manifest) == 12
    for doc in manifest:
        assert (out / doc["file"]).exists()
    assert any(d["contains_injection_attempt"] for d in manifest)
    assert any(not d["contains_injection_attempt"] for d in manifest)


@pytest.mark.integration
def test_structured_fields_extracted_accurately(setup) -> None:  # type: ignore[no-untyped-def]
    data, out, manifest = setup
    quotes = data["supplier_quotes"].set_index("quote_id")
    extractor = QuoteExtractor()
    for doc in manifest[:6]:
        result = extractor.extract(out / doc["file"])
        q = quotes.loc[doc["quote_id"]]
        assert result.fields["quote_id"].value == doc["quote_id"]
        assert result.fields["part_id"].value == doc["part_id"]
        assert float(result.fields["unit_price"].value) == pytest.approx(
            float(q["quoted_price"]), abs=1e-4
        )
        assert int(result.fields["lead_time_days"].value) == int(q["quoted_lead_time_days"])
        assert result.fields["currency"].value == q["currency"]


@pytest.mark.integration
def test_evidence_and_page_numbers_recorded(setup) -> None:  # type: ignore[no-untyped-def]
    _, out, manifest = setup
    result = QuoteExtractor().extract(out / manifest[0]["file"])
    price = result.fields["unit_price"]
    assert price.page_number == 1
    assert price.evidence_line and "Unit Price" in price.evidence_line
    assert price.confidence >= 0.8


@pytest.mark.integration
def test_injection_flagged_but_extraction_unaffected(setup) -> None:  # type: ignore[no-untyped-def]
    data, out, manifest = setup
    quotes = data["supplier_quotes"].set_index("quote_id")
    extractor = QuoteExtractor()
    injected_docs = [d for d in manifest if d["contains_injection_attempt"]]
    assert injected_docs
    for doc in injected_docs:
        result = extractor.extract(out / doc["file"])
        assert result.injection_flagged, doc["file"]
        # the injection text told the AI to change the price — it must NOT change
        q = quotes.loc[doc["quote_id"]]
        assert float(result.fields["unit_price"].value) == pytest.approx(
            float(q["quoted_price"]), abs=1e-4
        )


@pytest.mark.integration
def test_clean_documents_not_flagged(setup) -> None:  # type: ignore[no-untyped-def]
    _, out, manifest = setup
    clean = [d for d in manifest if not d["contains_injection_attempt"]]
    for doc in clean:
        result = QuoteExtractor().extract(out / doc["file"])
        assert not result.injection_flagged, doc["file"]


@pytest.mark.integration
def test_erp_comparison_detects_price_discrepancy(setup) -> None:  # type: ignore[no-untyped-def]
    data, out, manifest = setup
    doc = manifest[0]
    result = QuoteExtractor().extract(out / doc["file"])
    sp = data["supplier_parts"].copy()
    # force a large ERP/document price gap
    mask = (sp["part_id"] == doc["part_id"]) & (sp["supplier_id"] == doc["supplier_id"])
    sp.loc[mask, "unit_price"] = float(result.fields["unit_price"].value) * 5
    discrepancies = compare_with_erp(result, sp, doc["supplier_id"])
    assert any(d["type"] == "price_discrepancy" for d in discrepancies)


@pytest.mark.integration
def test_missing_erp_relationship_reported() -> None:
    from bom_guardian.document_intelligence.extractor import ExtractedField, ExtractionResult

    result = ExtractionResult(source_file="x.pdf")
    result.fields["part_id"] = ExtractedField(
        name="part_id",
        value="PRT-UNKNOWN",
        confidence=0.95,
        evidence_line="Internal Part Reference: PRT-UNKNOWN",
        page_number=1,
        needs_review=False,
    )
    sp = pd.DataFrame(columns=["part_id", "supplier_id", "unit_price", "lead_time_days"])
    out = compare_with_erp(result, sp, "SUP00001")
    assert out[0]["type"] == "no_erp_relationship"


@pytest.mark.integration
def test_low_confidence_routed_for_review() -> None:
    from bom_guardian.document_intelligence.extractor import QuoteExtractor

    value, confidence = QuoteExtractor._validate("currency", "ZZZ")
    assert confidence < 0.8  # invalid currency must be routed for review
