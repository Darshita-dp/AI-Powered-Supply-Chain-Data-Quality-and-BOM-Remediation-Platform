"""Python-side normalization, mirroring the dbt staging macros."""

from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^A-Z0-9]")
_WS = re.compile(r"\s+")

ABBREVIATIONS = {
    "SS": "STAINLESS",
    "ALUM": "ALUMINUM",
    "MFG": "MANUFACTURING",
    "INCORPORATED": "INC",
    "CORPORATION": "CORP",
}


def _as_str(value: object) -> str:
    """Coerce to str, treating None/NaN/empty as ''."""
    if value is None or not isinstance(value, str):
        return ""
    return value


def norm_part_number(value: object) -> str:
    text = _as_str(value)
    if not text:
        return ""
    return _NON_ALNUM.sub("", text.upper().strip())


def norm_text(value: object) -> str:
    text = _as_str(value)
    if not text:
        return ""
    out = _WS.sub(" ", text.upper().strip())
    tokens = [ABBREVIATIONS.get(t, t) for t in out.split(" ")]
    return " ".join(tokens)


def tokens(value: object) -> set[str]:
    return {t for t in norm_text(value).replace("-", " ").split(" ") if t}
