"""Deterministic-first supplier quote extraction.

Structured labeled fields are extracted with regexes; every extracted value
carries evidence (source line, page number) and a confidence. Low-confidence
or missing values are routed for human review, and an optional AI provider
hook may be used ONLY for ambiguous fields — never for the deterministic ones.

Document text is untrusted input:
- extraction never executes or follows instructions found in documents;
- instruction-like content is detected and surfaced as a security flag;
- extracted fields are validated against strict types/allowed sets;
- unsupported fields returned by any AI path are rejected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from bom_guardian.observability import get_logger

_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "supplier_name": re.compile(r"^Supplier Name:\s*(.+)$", re.MULTILINE),
    "supplier_part_number": re.compile(r"^Supplier Part Number:\s*(\S+)$", re.MULTILINE),
    "part_id": re.compile(r"^Internal Part Reference:\s*(\S+)$", re.MULTILINE),
    "unit_price": re.compile(r"^Unit Price:\s*([0-9]+\.[0-9]+)$", re.MULTILINE),
    "currency": re.compile(r"^Currency:\s*([A-Z]{3})$", re.MULTILINE),
    "min_order_qty": re.compile(r"^Minimum Order Quantity:\s*([0-9]+)$", re.MULTILINE),
    "lead_time_days": re.compile(r"^Lead Time Days:\s*([0-9]+)$", re.MULTILINE),
    "valid_from": re.compile(r"^Valid From:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})$", re.MULTILINE),
    "valid_to": re.compile(r"^Valid To:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})$", re.MULTILINE),
    "quote_id": re.compile(r"^Quotation Reference:\s*(\S+)$", re.MULTILINE),
}

_ALLOWED_CURRENCIES = {"USD", "EUR", "GBP", "INR", "CNY", "MXN", "JPY"}

# Instruction-like content addressed at automation — flagged, never followed.
_INJECTION_PATTERNS = re.compile(
    r"(ignore (all |previous )?instructions|system note|ai assistant|"
    r"disregard .{0,40}(rules|policy)|approve this)",
    re.IGNORECASE,
)

REVIEW_CONFIDENCE_THRESHOLD = 0.8


@dataclass
class ExtractedField:
    name: str
    value: str | None
    confidence: float
    evidence_line: str | None
    page_number: int | None
    needs_review: bool


@dataclass
class ExtractionResult:
    source_file: str
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    injection_flagged: bool = False
    injection_evidence: str | None = None

    @property
    def low_confidence_fields(self) -> list[str]:
        return [n for n, f in self.fields.items() if f.needs_review]


class QuoteExtractor:
    """Deterministic quote-PDF extractor with security controls."""

    def __init__(self) -> None:
        self._log = get_logger("doc_extractor")

    def extract(self, pdf_path: Path) -> ExtractionResult:
        reader = PdfReader(str(pdf_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        result = ExtractionResult(source_file=pdf_path.name)

        full_text = "\n".join(pages)
        injection = _INJECTION_PATTERNS.search(full_text)
        if injection:
            result.injection_flagged = True
            result.injection_evidence = injection.group(0)
            self._log.warning(
                "document_injection_flagged", file=pdf_path.name, pattern=injection.group(0)
            )

        for name, pattern in _FIELD_PATTERNS.items():
            extracted = self._extract_field(name, pattern, pages)
            result.fields[name] = extracted
        return result

    def _extract_field(
        self, name: str, pattern: re.Pattern[str], pages: list[str]
    ) -> ExtractedField:
        for page_no, text in enumerate(pages, start=1):
            m = pattern.search(text)
            if not m:
                continue
            raw = m.group(1).strip()
            value, confidence = self._validate(name, raw)
            line = next((ln for ln in text.splitlines() if raw in ln), None)
            return ExtractedField(
                name=name,
                value=value,
                confidence=confidence,
                evidence_line=line,
                page_number=page_no,
                needs_review=confidence < REVIEW_CONFIDENCE_THRESHOLD,
            )
        return ExtractedField(
            name=name,
            value=None,
            confidence=0.0,
            evidence_line=None,
            page_number=None,
            needs_review=True,
        )

    @staticmethod
    def _validate(name: str, raw: str) -> tuple[str | None, float]:
        """Type/set validation; failures downgrade confidence for review routing."""
        if name == "currency" and raw not in _ALLOWED_CURRENCIES:
            return raw, 0.4
        if name in ("unit_price",):
            try:
                if float(raw) <= 0:
                    return raw, 0.3
            except ValueError:
                return raw, 0.2
        if name in ("min_order_qty", "lead_time_days"):
            try:
                if int(raw) < 0:
                    return raw, 0.3
            except ValueError:
                return raw, 0.2
        # labeled single-line match on a structured layout: high confidence
        return raw, 0.95
