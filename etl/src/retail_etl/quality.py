"""Data-quality helpers. Every transform returns its gold rows plus DQ findings in one common format."""
from __future__ import annotations

import pandas as pd

DQ_COLUMNS = ["object", "key", "rule", "severity", "message"]
# severity: ERROR = row excluded from gold and blocks the load gate; WARNING = loaded, reported to the data owner


def gtin_check_digit(body: str) -> int:
    """GS1 check digit for a GTIN body (UPC-A body = 11 digits, EAN-13 body = 12 digits)."""
    digits = [int(c) for c in body]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10


def is_valid_gtin(code: str | int | float | None) -> bool:
    """True for a numeric 8/12/13/14-digit GTIN with a correct check digit."""
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return False
    s = str(code).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit() or len(s) not in (8, 12, 13, 14):
        return False
    return gtin_check_digit(s[:-1]) == int(s[-1])


def finding(obj: str, key: str, rule: str, severity: str, message: str) -> dict:
    return {"object": obj, "key": key, "rule": rule, "severity": severity, "message": message}


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=DQ_COLUMNS)
