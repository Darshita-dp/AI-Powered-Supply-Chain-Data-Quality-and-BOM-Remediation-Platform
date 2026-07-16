"""Compare extracted document values against ERP supplier-part records,
producing discrepancy records for the quality workflow."""

from __future__ import annotations

import pandas as pd

from bom_guardian.document_intelligence.extractor import ExtractionResult

PRICE_TOLERANCE = 0.10  # 10% relative
LEAD_TIME_TOLERANCE_DAYS = 7


def compare_with_erp(
    extraction: ExtractionResult,
    supplier_parts: pd.DataFrame,
    supplier_id: str,
) -> list[dict]:
    """Return discrepancy dicts (empty when doc and ERP agree within tolerance)."""
    part_field = extraction.fields.get("part_id")
    if part_field is None or part_field.value is None:
        return [
            {
                "type": "unmatchable_document",
                "source_file": extraction.source_file,
                "detail": "no internal part reference extracted",
            }
        ]
    erp = supplier_parts[
        (supplier_parts["part_id"] == part_field.value)
        & (supplier_parts["supplier_id"] == supplier_id)
    ]
    if erp.empty:
        return [
            {
                "type": "no_erp_relationship",
                "source_file": extraction.source_file,
                "part_id": part_field.value,
                "supplier_id": supplier_id,
                "detail": "document references a part this supplier does not supply in ERP",
            }
        ]

    row = erp.iloc[0]
    discrepancies: list[dict] = []

    price_field = extraction.fields.get("unit_price")
    if price_field and price_field.value is not None:
        doc_price = float(price_field.value)
        erp_price = float(row["unit_price"])
        if erp_price > 0 and abs(doc_price - erp_price) / erp_price > PRICE_TOLERANCE:
            discrepancies.append(
                {
                    "type": "price_discrepancy",
                    "source_file": extraction.source_file,
                    "part_id": part_field.value,
                    "supplier_id": supplier_id,
                    "document_value": doc_price,
                    "erp_value": erp_price,
                    "evidence_line": price_field.evidence_line,
                    "page_number": price_field.page_number,
                    "confidence": price_field.confidence,
                }
            )

    lt_field = extraction.fields.get("lead_time_days")
    if lt_field and lt_field.value is not None:
        doc_lt = int(lt_field.value)
        erp_lt = int(row["lead_time_days"])
        if abs(doc_lt - erp_lt) > LEAD_TIME_TOLERANCE_DAYS:
            discrepancies.append(
                {
                    "type": "lead_time_discrepancy",
                    "source_file": extraction.source_file,
                    "part_id": part_field.value,
                    "supplier_id": supplier_id,
                    "document_value": doc_lt,
                    "erp_value": erp_lt,
                    "evidence_line": lt_field.evidence_line,
                    "page_number": lt_field.page_number,
                    "confidence": lt_field.confidence,
                }
            )
    return discrepancies
