"""Evidence-first extraction of a small set of financial statement figures.

This module proposes candidates; it does not silently certify values. Every
candidate includes its page, source row, label matched, confidence and selection
method so the UI can ask a person to verify it before saving.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

try:
    import pdfplumber
except ImportError:  # Text extraction fallback remains available via pypdf.
    pdfplumber = None


FINANCIAL_ALIASES = {
    "CURRENT_ASSETS": [
        "total current assets", "current assets",
    ],
    "CURRENT_LIABILITIES": [
        "total current liabilities", "current liabilities",
    ],
    "INVENTORY": [
        "inventories", "inventory", "stocks",
    ],
    "REVENUE": [
        "revenue from operations", "total revenue from operations",
        "revenue from operation", "revenue", "turnover",
    ],
    "NET_PROFIT": [
        "profit after tax", "profit for the year", "net profit",
        "profit for the period",
    ],
    "TOTAL_DEBT": [
        "total borrowings", "total debt", "borrowings and lease liabilities",
        "borrowings",
    ],
    "EQUITY": [
        "total equity", "total shareholders' equity",
        "total shareholders equity", "equity attributable to owners",
        "shareholders' funds",
    ],
    "OPERATING_CASH_FLOW": [
        "net cash flows generated from operating activities",
        "net cash generated from operating activities",
        "net cash flows from operating activities",
        "net cash from operating activities",
        "net cash provided by operating activities",
    ],
}

# Patterns only accept an amount following a matched label. Page numbers and
# dates before the label therefore cannot accidentally become the value.
AMOUNT_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:\(\s*-?\s*(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?\s*\)"
    r"|-?\s*(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"
    r"|—|–|nil)"
    r"(?![A-Za-z0-9])",
    re.IGNORECASE,
)
NOTE_PAREN_RE = re.compile(r"\((?:\s*(?:note|refer|see|page)\b[^)]*)\)", re.I)
PREFIX_RE = re.compile(
    r"^\s*(?:(?:\(?[a-z]\)|\(?\d+\)?[.)])\s+|[•▪●\-–]\s*)+",
    re.I,
)
YEAR_RANGE_RE = re.compile(r"\b(20\d{2})\s*[-/–]\s*(\d{2,4})\b")


def _normalize(value: str) -> str:
    value = (value or "").replace("\u00a0", " ").replace("\u2019", "'")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def _clean_row_start(value: str) -> str:
    return PREFIX_RE.sub("", (value or "").strip()).strip()


def _match_alias(row_text: str, code: str) -> tuple[str | None, int]:
    """Match a dictionary alias at the beginning of a statement row.

    Anchoring the match prevents a sentence such as '... current assets ...'
    in narrative text from being treated as a financial-statement row.
    """
    clean = _clean_row_start(row_text)
    normalized = _normalize(clean)
    for alias in sorted(FINANCIAL_ALIASES[code], key=len, reverse=True):
        a = _normalize(alias)
        if normalized == a or normalized.startswith(a + " ") or normalized.startswith(a + "|"):
            # Do not interpret more specific concepts as a generic parent item.
            tail = normalized[len(a):].lstrip(" |:-")
            if code == "CURRENT_ASSETS" and tail.startswith(("ratio", "turnover")):
                continue
            if code == "CURRENT_LIABILITIES" and tail.startswith(("ratio", "turnover")):
                continue
            if code == "REVENUE" and a == "revenue" and normalized.startswith(
                ("revenue from", "revenue attributable", "revenue per", "revenue growth")
            ):
                continue
            if code == "NET_PROFIT" and any(
                phrase in normalized[:len(a) + 30]
                for phrase in ("continuing operations", "discontinued operations")
            ):
                continue
            return alias, len(_clean_row_start(row_text)) - len(clean)
    return None, -1


def _parse_amount(token: str, allow_negative: bool = False) -> float | None:
    token = (token or "").strip()
    if not token or token.casefold() in {"nil", "—", "–", "-"}:
        return None
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("() ").replace(",", "").replace(" ", "")
    try:
        result = float(token)
    except ValueError:
        return None
    if negative:
        result = -abs(result)
    if result < 0 and not allow_negative:
        return None
    return result


def _amounts_after(text: str, alias: str, allow_negative: bool = False) -> list[float]:
    normalized = _clean_row_start(text)
    # Remove note references such as '(Note 12)' before reading numbers.
    normalized = NOTE_PAREN_RE.sub(" ", normalized)
    match = re.match(re.escape(alias), normalized, re.I)
    if not match:
        # Case/spacing can differ from the source alias.
        match = re.search(re.escape(alias), normalized, re.I)
    if not match:
        return []
    tail = normalized[match.end():]
    # Remove plain note markers before amount parsing as well.
    tail = re.sub(r"\bnotes?\s+\d+\b", " ", tail, flags=re.I)
    results = []
    for item in AMOUNT_RE.finditer(tail):
        value = _parse_amount(item.group(0), allow_negative=allow_negative)
        if value is not None:
            results.append(value)
    return results


def _target_year(fiscal_year: str) -> int | None:
    value = str(fiscal_year or "")
    period = YEAR_RANGE_RE.search(value)
    if period:
        end = period.group(2)
        return int(end) if len(end) == 4 else int(period.group(1)[:2] + end)
    years = re.findall(r"(?<!\d)(20\d{2})(?!\d)", value)
    return int(years[-1]) if years else None


def _years_in_header(cell: str) -> set[int]:
    text = str(cell or "")
    result: set[int] = set()
    period = YEAR_RANGE_RE.search(text)
    if period:
        end = period.group(2)
        result.add(int(end) if len(end) == 4 else int(period.group(1)[:2] + end))
        return result
    # Dates such as 'As at 31 March 2026' resolve to 2026.
    for year in re.findall(r"\b20\d{2}\b", text):
        result.add(int(year))
    return result


def _page_scope(page_text: str) -> str | None:
    text = _normalize(page_text)
    patterns = [
        (r"\bstand[\s-]?alone\b.{0,70}\b(balance sheet|financial statements|statement of|profit and loss|cash flows)\b", "STANDALONE"),
        (r"\b(balance sheet|financial statements|statement of|profit and loss|cash flows)\b.{0,70}\bstand[\s-]?alone\b", "STANDALONE"),
        (r"\bconsolidated\b.{0,70}\b(balance sheet|financial statements|statement of|profit and loss|cash flows)\b", "CONSOLIDATED"),
        (r"\b(balance sheet|financial statements|statement of|profit and loss|cash flows)\b.{0,70}\bconsolidated\b", "CONSOLIDATED"),
    ]
    for pattern, scope in patterns:
        if re.search(pattern, text):
            return scope
    return None


def _statement_matches(code: str, page_text: str) -> bool:
    text = _normalize(page_text)
    if code in {"CURRENT_ASSETS", "CURRENT_LIABILITIES", "INVENTORY", "TOTAL_DEBT", "EQUITY"}:
        return any(term in text for term in ("balance sheet", "assets and liabilities", "current assets"))
    if code in {"REVENUE", "NET_PROFIT"}:
        return any(term in text for term in (
            "statement of profit and loss", "statement of profit or loss",
            "income statement", "profit and loss account",
        ))
    return any(term in text for term in (
        "cash flow statement", "statement of cash flows", "cash flows from operating activities",
    ))


def _unit_hint(document_text: str) -> tuple[str, str]:
    text = _normalize(document_text)
    if re.search(r"(?:₹|rs\.?|inr).{0,25}\b(?:crore|crores|crs?)\b|\b(?:amounts?|figures?)\s+in\s+crores?\b", text):
        return "INR crore", "The PDF appears to state amounts in crore; verify this against the statement heading."
    if re.search(r"(?:₹|rs\.?|inr).{0,25}\bmillions?\b|\b(?:amounts?|figures?)\s+in\s+millions?\b", text):
        return "INR million", "The PDF appears to state amounts in million; verify this against the statement heading."
    if re.search(r"(?:₹|rs\.?|inr).{0,25}\blakhs?\b|\b(?:amounts?|figures?)\s+in\s+lakhs?\b", text):
        return "INR lakh", "The PDF appears to state amounts in lakh; verify this against the statement heading."
    return "INR crore", "Unit could not be inferred reliably; the form defaults to INR crore. Check the statement heading."


def _read_pdf_pages(path: str | Path) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    path = Path(path)
    if pdfplumber is not None:
        try:
            with pdfplumber.open(str(path)) as pdf:
                for number, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    tables = []
                    try:
                        for table in page.extract_tables() or []:
                            cleaned = [
                                [str(cell or "").strip() for cell in row]
                                for row in table if any(str(cell or "").strip() for cell in row)
                            ]
                            if cleaned:
                                tables.append(cleaned)
                    except Exception:
                        # Some annual-report layouts confuse table detection.
                        tables = []
                    pages.append({"page": number, "text": text, "tables": tables})
            if pages:
                return pages
        except Exception:
            pages = []

    # Fallback for PDFs where pdfplumber cannot open/extract the document.
    reader = PdfReader(str(path), strict=False)
    for number, page in enumerate(reader.pages, start=1):
        pages.append({
            "page": number,
            "text": page.extract_text() or "",
            "tables": [],
        })
    return pages


def _candidate_score(
    code: str, page_text: str, target_year: int | None,
    statement_scope: str, year_confirmed: bool, from_table: bool,
) -> tuple[float, str]:
    score = 0.55 if from_table else 0.40
    reasons = ["table row" if from_table else "text row", "label matched at row start"]
    detected_scope = _page_scope(page_text)
    if detected_scope == statement_scope:
        score += 0.18
        reasons.append("statement scope matches")
    elif detected_scope and detected_scope != statement_scope:
        score -= 0.30
        reasons.append(f"page appears to be {detected_scope.lower()}")
    if _statement_matches(code, page_text):
        score += 0.12
        reasons.append("statement section matches")
    if year_confirmed:
        score += 0.18
        reasons.append(f"target year {target_year} found in table header")
    elif target_year:
        score -= 0.12
        reasons.append(f"target year {target_year} column is not confirmed")
    else:
        reasons.append("target year was not supplied")
    return round(max(0.05, min(score, 0.99)), 2), "; ".join(reasons)


def extract_financial_items(
    path: str | Path, fiscal_year: str, statement_scope: str = "CONSOLIDATED",
) -> tuple[dict[str, float], dict[str, dict[str, Any]], dict[str, str]]:
    """Return (suggested values, evidence per item, document metadata).

    Table candidates use column year headings when pdfplumber exposes them.
    Text-line candidates are a fallback. The UI must require human review.
    """
    pages = _read_pdf_pages(path)
    all_text = "\n".join(page["text"] for page in pages)
    if not all_text.strip():
        raise ValueError(
            "No selectable text was found. This may be a scanned PDF; OCR is not enabled."
        )

    target_year = _target_year(fiscal_year)
    statement_scope = statement_scope.upper()
    if statement_scope not in {"STANDALONE", "CONSOLIDATED"}:
        statement_scope = "CONSOLIDATED"

    candidates: dict[str, list[dict[str, Any]]] = {code: [] for code in FINANCIAL_ALIASES}

    for page in pages:
        page_number = page["page"]
        page_text = page["text"] or ""
        page_scope_context = _page_scope(page_text)

        for table in page["tables"]:
            # Map header cells to fiscal-year-end values. Most annual reports
            # put current year first; use that only if no header mapping exists.
            year_columns: dict[int, int] = {}
            for header_row in table[:6]:
                for col, cell in enumerate(header_row):
                    for year in _years_in_header(cell):
                        year_columns[col] = year

            for row_index, row in enumerate(table):
                nonempty = [cell for cell in row if cell.strip()]
                if not nonempty:
                    continue
                row_text = " | ".join(row)
                for code in FINANCIAL_ALIASES:
                    alias, _ = _match_alias(row_text, code)
                    if not alias:
                        # Table cells can split label and amounts; match a
                        # leading label cell directly before joining values.
                        for cell in row:
                            alias, _ = _match_alias(cell, code)
                            if alias:
                                break
                    if not alias:
                        continue

                    label_col = next(
                        (i for i, cell in enumerate(row)
                         if _match_alias(cell, code)[0] is not None),
                        0,
                    )
                    amount_cells = []
                    selected_value = None
                    year_confirmed = False
                    # Use the same column as the target-year header when
                    # available; do not blindly pick the first number.
                    target_col = next(
                        (col for col, year in year_columns.items() if year == target_year),
                        None,
                    ) if target_year else None
                    if target_col is not None and target_col < len(row) and target_col > label_col:
                        selected_value = _parse_amount(row[target_col], allow_negative=code in {"NET_PROFIT", "OPERATING_CASH_FLOW"})
                        year_confirmed = selected_value is not None
                    if selected_value is None:
                        for cell in row[label_col + 1:]:
                            value = _parse_amount(cell, allow_negative=code in {"NET_PROFIT", "OPERATING_CASH_FLOW"})
                            if value is not None:
                                amount_cells.append(value)
                        if amount_cells:
                            selected_value = amount_cells[0]
                    if selected_value is None:
                        amount_cells = _amounts_after(row_text, alias, allow_negative=code in {"NET_PROFIT", "OPERATING_CASH_FLOW"})
                        if amount_cells:
                            selected_value = amount_cells[0]
                    if selected_value is None:
                        continue

                    score, reason = _candidate_score(
                        code, page_text, target_year, statement_scope,
                        year_confirmed, True,
                    )
                    candidates[code].append({
                        "value": selected_value,
                        "label": alias,
                        "page": page_number,
                        "snippet": row_text[:500],
                        "confidence": score,
                        "reason": reason,
                        "method": "table",
                        "scope_seen": page_scope_context or "Not detected",
                        "scope_confirmed": page_scope_context == statement_scope,
                        "year_confirmed": year_confirmed,
                    })

        # Fallback: only inspect statement-like rows, not arbitrary prose where
        # the alias occurs in the middle of a sentence.
        lines = [re.sub(r"\s+", " ", line).strip() for line in page_text.splitlines() if line.strip()]
        for line in lines:
            for code in FINANCIAL_ALIASES:
                alias, _ = _match_alias(line, code)
                if not alias:
                    continue
                amounts = _amounts_after(line, alias, allow_negative=code in {"NET_PROFIT", "OPERATING_CASH_FLOW"})
                if not amounts:
                    continue
                # If the row carries several years, this method cannot safely
                # align them to columns. Mark it lower confidence for review.
                score, reason = _candidate_score(
                    code, page_text, target_year, statement_scope, False, False,
                )
                candidates[code].append({
                    "value": amounts[0],
                    "label": alias,
                    "page": page_number,
                    "snippet": line[:500],
                    "confidence": score,
                    "reason": reason,
                    "method": "text",
                    "scope_seen": page_scope_context or "Not detected",
                    "scope_confirmed": page_scope_context == statement_scope,
                    "year_confirmed": False,
                })

    evidence: dict[str, dict[str, Any]] = {}
    values: dict[str, float] = {}
    for code, options in candidates.items():
        if not options:
            continue
        # Prefer a correctly aligned table row. Ties prefer the highest confidence.
        options.sort(
            key=lambda item: (
                item["confidence"],
                item["method"] == "table",
                item["scope_seen"] == statement_scope,
            ),
            reverse=True,
        )
        best = options[0]
        # Only pre-fill with reasonably supported candidates. Others are shown
        # as evidence for the user but must be manually entered.
        alternatives = [
            {
                "value": item["value"],
                "label": item["label"],
                "page": item["page"],
                "confidence": item["confidence"],
                "method": item["method"],
                "year_confirmed": item.get("year_confirmed", False),
                "scope_confirmed": item.get("scope_confirmed", False),
                "snippet": item["snippet"],
            }
            for item in options[1:4]
        ]
        # Similar-strength candidates with different values are ambiguous.
        best["alternatives"] = alternatives
        best["ambiguous"] = any(
            item["value"] != best["value"]
            and abs(item["confidence"] - best["confidence"]) < 0.12
            for item in alternatives
        )
        evidence[code] = best
        # Never auto-fill unless the exact fiscal-year column was identified
        # and similarly ranked candidates do not disagree.
        if (best["confidence"] >= 0.75 and best.get("year_confirmed")
                and best.get("scope_confirmed") and not best["ambiguous"]):
            values[code] = best["value"]

    unit, unit_note = _unit_hint(all_text)
    meta = {
        "page_count": str(len(pages)),
        "target_year": str(target_year or "Not detected"),
        "statement_scope": statement_scope,
        "unit_hint": unit,
        "unit_note": unit_note,
        "text_characters": str(len(all_text)),
    }
    return values, evidence, meta
