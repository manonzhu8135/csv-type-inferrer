"""Infer per-column types for CSV data.

Public API
----------
- ``infer_types(csv_text, *, delimiter=',', has_header=True, strict=True) -> dict[str, str]``
- ``infer_row_type(values, *, strict=True) -> str``
- ``ColumnTypes``: namespace of supported type-name constants.

Supported types
---------------
- ``"boolean"``: ``"true"``/``"false"``/``"yes"``/"no"`` (case-insensitive), or the bare strings ``"0"``/"1"``.
- ``"int"``: an optional sign followed by decimal digits.
- ``"float"``: integers plus decimal floats, scientific notation, leading/trailing dots, and ``"inf"``/"-inf"``/"nan"``.
- ``"date"``: ``YYYY-MM-DD`` with month 01-12 and day 01-31 (calendar validity not checked).
- ``"string"``: anything else, including empty values.

Interpretations picked where the brief is ambiguous
---------------------------------------------------
1. Strict column inference: *every* non-empty value in a column must agree on a single
   non-string type. A single mismatch demotes the whole column to ``"string"``. The
   alternative — narrowing per value and reporting a union — complicates the output shape
   and is not what callers of a *column* inferrer usually want.
2. Empty values (``""``) are skipped at the column level and do not force ``"string"``;
   at the single-value level they report ``"string"``. This matches the intuition that a
   missing cell should not change a column's overall type.
3. ``"0"`` and ``"1"`` are boolean when strict column inference is on — they look like
   booleans in real CSVs more often than they look like plain ints, and disambiguating by
   counting would require sampling thresholds the brief does not specify.
"""

from __future__ import annotations

import csv as _csv
from io import StringIO


class ColumnTypes:
    """Type-name constants returned by this library.

    Kept as a class rather than a module-level enum so that the returned strings are
    plain ``str`` (easier to compare and serialize) while still being discoverable.
    """

    BOOLEAN = "boolean"
    INT = "int"
    FLOAT = "float"
    DATE = "date"
    STRING = "string"

    ALL = (BOOLEAN, INT, FLOAT, DATE, STRING)


def _is_boolean(s: str) -> bool:
    """True if *s* is one of the boolean literals we recognise (case-insensitive)."""
    return s.lower() in ("true", "false", "yes", "no", "0", "1")


def _is_int(s: str) -> bool:
    """True if *s* is a decimal integer with an optional sign."""
    if s in ("+", "-"):
        return False
    body = s[1:] if s[0] in "+-" else s
    return body.isdigit() and body != ""


def _is_float(s: str) -> bool:
    """True if *s* parses as a float via ``float()``.

    Note: this deliberately accepts ``"inf"``, ``"nan"`` etc. as floats so a column like
    ``["1.5", "inf", "2.5"]`` still reports ``"float"`` rather than ``"string"``.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def _is_date(s: str) -> bool:
    """True if *s* is ``YYYY-MM-DD`` with month 01-12 and day 01-31.

    Calendar validity (Feb 30, Apr 31, leap years) is NOT checked — the brief says
    ``date``, not ``calendar-accurate date``,``, and accepting the easy shape keeps the
    matcher cheap and dependency-free.
    """
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        return False
    y, m, d = s[0:4], s[5:7], s[8:10]
    if not (y.isdigit() and m.isdigit() and d.isdigit()):
        return False
    if len(y) != 4 or len(m) != 2 or len(d) != 2:
        return False
    mm, dd = int(m), int(d)
    return 1 <= mm <= 12 and 1 <= dd <= 31


def infer_row_type(values, *, strict: bool = True) -> str:
    """Return the inferred type of a single row of cells.

    Aggregates multiple cells by strict intersection: all non-empty cells must
    agree on the same non-string type. Returns ``ColumnTypes.STRING`` if the row
    is empty, mixed, or cannot be narrowed.

    The ``strict`` flag is accepted for symmetry with ``infer_types`` but does not
    change behaviour here — a single row has no other rows to be stricter or looser
    against. It is kept so callers can pass the same options to both functions.
    """
    normalized = [
        v.strip() if isinstance(v, str) else str(v).strip() for v in values
    ]
    non_empty = [v for v in normalized if v != ""]
    if not non_empty:
        return ColumnTypes.STRING

    candidate: str | None = None
    for v in non_empty:
        t = _classify(v)
        if t == ColumnTypes.STRING:
            return ColumnTypes.STRING
        if candidate is None:
            candidate = t
        elif candidate != t:
            return ColumnTypes.STRING
    assert candidate is not None  # guaranteed by the non_empty check above
    return candidate


def _classify(s: str) -> str:
    """Classify a single normalized, non-empty string value."""
    if _is_boolean(s):
        return ColumnTypes.BOOLEAN
    if _is_int(s):
        return ColumnTypes.INT
    if _is_float(s):
        return ColumnTypes.FLOAT
    if _is_date(s):
        return ColumnTypes.DATE
    return ColumnTypes.STRING


def _maybe_narrow(candidate: str | None, value: str) -> str | None:
    """Update the current column candidate given a new value.

    Returns ``None`` to mean "give up — this column is string". The narrowing rule
    is: ints beat booleans (so a column of explicit ints plus ``0``/``1`` stays
    int); otherwise the first-seen non-string type wins unless a later value
    disagrees.
    """
    t = _classify(value)
    if t == ColumnTypes.STRING:
        return None
    if candidate is None:
        return t
    if candidate == t:
        return candidate
    # Boolean and int both match "0"/"1". If a column has ints and a literal 0/1,
    # keep it int only when every value so far is boolean; otherwise the int
    # context wins.
    if candidate == ColumnTypes.BOOLEAN and t == ColumnTypes.INT:
        return t
    if candidate == ColumnTypes.INT and t == ColumnTypes.BOOLEAN:
        return candidate
    return None


def infer_types(
    csv_text: str,
    *,
    delimiter: str = ",",
    has_header: bool = True,
    strict: bool = True,
) -> dict[str, str]:
    """Infer per-column types from CSV text.

    Parameters
    ----------
    csv_text:
        Raw CSV text (not a path). Use ``pathlib.Path.read_text`` to load a file.
    delimiter:
        Field delimiter passed to :mod:`csv`. Defaults to ``","``.
    has_header:
        If True (default), the first row is used as column names and excluded
        from inference. If False, columns are named ``col_0``, ``col_1``, ....
    strict:
        Reserved for API symmetry. Column inference is always strict — every
        non-empty value in a column must agree. Kept as a parameter so callers
        can pass it without breaking if a relaxed mode is added later.

    Returns
    -------
    dict[str, str]
        Maps column name to one of the :class:`ColumnTypes` constants.
        An empty CSV (only a header, or no rows) yields an empty dict.
    """
    reader = _csv.reader(StringIO(csv_text), delimiter=delimiter)
    rows: list[list[str]] = [row for row in reader]
    if not rows:
        return {}

    if has_header:
        header, data_rows = rows[0], rows[1:]
    else:
        header = [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows

    if not data_rows:
        return {}

    width = len(header)
    result: dict[str, str] = {}
    for col_idx in range(width):
        candidate: str | None = None
        saw_any = False
        for row in data_rows:
            value = row[col_idx].strip() if col_idx < len(row) else ""
            if value == "":
                continue
            saw_any = True
            candidate = _maybe_narrow(candidate, value)
            if candidate is None:
                break
        name = header[col_idx] if col_idx < len(header) else f"col_{col_idx}"
        if not saw_any or candidate is None:
            result[name] = ColumnTypes.STRING
        else:
            result[name] = candidate
    return result
