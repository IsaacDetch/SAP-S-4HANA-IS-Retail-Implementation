"""Reconciliation: control totals per object, cross-object checks and source-vs-target comparison."""
from __future__ import annotations

import pandas as pd

from .transform import INVENTORY_ACCOUNT, MIGRATION_CLEARING

RECON_COLUMNS = ["object", "check", "expected", "actual", "difference", "status"]


def _row(obj, check, expected, actual, tol=0.0):
    diff = round(float(actual) - float(expected), 2)
    return {"object": obj, "check": check, "expected": expected, "actual": actual, "difference": diff, "status": "PASS" if abs(diff) <= tol else "FAIL"}


def control_totals(gold: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Counts and amounts that must match after the Migration Cockpit transfer (compared with S/4 extracts)."""
    t = {f"{k}.rows": float(len(v)) for k, v in gold.items()}
    if "article" in gold:
        a = gold["article"]
        t["article.generic"] = float((a["ATTYP"] == "01").sum()); t["article.variant"] = float((a["ATTYP"] == "02").sum())
    if "inventory_balance" in gold:
        t["inventory_balance.qty"] = round(float(gold["inventory_balance"]["ERFMG"].sum()), 3)
        t["inventory_balance.value"] = round(float(gold["inventory_balance"]["EXBWR"].sum()), 2)
    if "sales_price" in gold:
        t["sales_price.sum"] = round(float(gold["sales_price"]["KBETR"].sum()), 2)
    if "gl_balance" in gold:
        g = gold["gl_balance"]; t["gl_balance.debit"] = round(float(g.loc[g["SHKZG"] == "S", "WRBTR"].sum()), 2)
    return t


def source_vs_gold(silver: dict[str, pd.DataFrame], gold: dict[str, pd.DataFrame], dq: pd.DataFrame) -> pd.DataFrame:
    """Every source row is either in gold or rejected with an ERROR finding (no silent drops)."""
    rows = []
    err = dq[dq["severity"] == "ERROR"]
    if "stores" in silver and "site" in gold:
        rows.append(_row("site", "source rows = gold + rejected", len(silver["stores"]), len(gold["site"]) + (err["object"] == "site").sum()))
    if "vendors" in silver and "supplier" in gold:
        rows.append(_row("supplier", "source rows = gold + rejected", len(silver["vendors"]), len(gold["supplier"]) + (err["object"] == "supplier").sum()))
    if "items" in silver and "article" in gold:
        rejected_variants = err.loc[err["object"] == "article", "key"].nunique()
        rows.append(_row("article", "source variants = gold variants + rejected", len(silver["items"]), int((gold["article"]["ATTYP"] == "02").sum()) + rejected_variants))
    return pd.DataFrame(rows, columns=RECON_COLUMNS)


def cross_object_checks(silver: dict[str, pd.DataFrame], gold: dict[str, pd.DataFrame], rules: dict) -> pd.DataFrame:
    rows = []
    if "inventory_balance" in gold and "trial_balance" in silver:
        tb = silver["trial_balance"]
        legacy_inv = [k for k, v in rules["gl_account"].items() if v == INVENTORY_ACCOUNT]
        legacy_val = round(float((tb.loc[tb["legacy_account"].astype(str).isin(legacy_inv), "debit"].fillna(0)
                                  - tb.loc[tb["legacy_account"].astype(str).isin(legacy_inv), "credit"].fillna(0)).sum()), 2)
        stock_val = round(float(gold["inventory_balance"]["EXBWR"].sum()), 2)
        rows.append(_row("inventory_balance", "stock value (561) = legacy G/L inventory", legacy_val, stock_val, tol=1.0))
    if "gl_balance" in gold and "inventory_balance" in gold:
        g = gold["gl_balance"]
        clearing_gl = round(float((g.loc[g["HKONT"] == MIGRATION_CLEARING, "WRBTR"] * g.loc[g["HKONT"] == MIGRATION_CLEARING, "SHKZG"].map({"S": 1, "H": -1})).sum()), 2)
        clearing_stock = -round(float(gold["inventory_balance"]["EXBWR"].sum()), 2)   # 561 posts Dr inventory / Cr clearing
        rows.append(_row("gl_balance", f"migration clearing {MIGRATION_CLEARING} nets to zero", 0, round(clearing_gl + clearing_stock, 2), tol=1.0))
    return pd.DataFrame(rows, columns=RECON_COLUMNS)


def compare_with_target(expected: dict[str, float], actual: dict[str, float]) -> pd.DataFrame:
    """Compare control totals with the same totals extracted from S/4HANA after the transfer (notebook 04)."""
    rows = [_row(k.split(".")[0], k, v, actual.get(k, 0.0), tol=0.01) for k, v in expected.items()]
    return pd.DataFrame(rows, columns=RECON_COLUMNS)
