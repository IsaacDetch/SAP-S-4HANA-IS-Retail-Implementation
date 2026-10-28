"""Local end-to-end run of the migration transforms (bronze/silver CSV -> gold CSV + DQ + reconciliation).

In Azure the same steps run as ADF pipeline pl_00_master_migration -> Databricks notebooks 01-04.
Usage: python -m retail_etl.pipeline --source etl/sample_data/legacy --out etl/sample_output
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import reconcile, transform
from .rules import load_rules

SOURCES = {"stores": "legacy_stores.csv", "vendors": "legacy_vendors.csv", "items": "legacy_items.csv",
           "onhand": "legacy_onhand.csv", "trial_balance": "legacy_trial_balance.csv"}


def read_silver(source: Path) -> dict[str, pd.DataFrame]:
    """Bronze -> silver: read as text, trim, standardise empty values (type casting happens in the transforms)."""
    silver = {}
    for k, f in SOURCES.items():
        df = pd.read_csv(source / f, dtype=str, keep_default_na=False)
        silver[k] = df.apply(lambda s: s.str.strip())
    for col in ("debit", "credit"):
        silver["trial_balance"][col] = pd.to_numeric(silver["trial_balance"][col].replace("", "0"))
    return silver


def run(source: Path, out: Path, posting_date: str = "2026-06-30", price_valid_from: str = "2026-07-01") -> dict:
    rules = load_rules()
    s = read_silver(source)
    gold, dqs = {}, []
    gold["site"], d = transform.sites(s["stores"], rules); dqs.append(d)
    gold["supplier"], d = transform.suppliers(s["vendors"], rules); dqs.append(d)
    gold["article"], d = transform.articles(s["items"], rules); dqs.append(d)
    gold["sales_price"], d = transform.sales_prices(s["items"], gold["article"], rules, price_valid_from); dqs.append(d)
    gold["inventory_balance"], d = transform.inventory_balances(s["onhand"], gold["article"], gold["site"], rules, posting_date); dqs.append(d)
    gold["gl_balance"], d = transform.gl_balances(s["trial_balance"], rules, posting_date); dqs.append(d)
    dq = pd.concat([x for x in dqs if not x.empty], ignore_index=True)
    recon = pd.concat([reconcile.source_vs_gold(s, gold, dq), reconcile.cross_object_checks(s, gold, rules)], ignore_index=True)
    totals = reconcile.control_totals(gold)
    out.mkdir(parents=True, exist_ok=True)
    for k, v in gold.items():
        v.to_csv(out / f"gold_{k}.csv", index=False)
    dq.to_csv(out / "dq_findings.csv", index=False)
    recon.to_csv(out / "reconciliation.csv", index=False)
    pd.Series(totals, name="value").to_csv(out / "control_totals.csv", index_label="control_total")
    gate_ok = bool((recon["status"] == "PASS").all())
    return {"gold": gold, "dq": dq, "recon": recon, "totals": totals, "gate_ok": gate_ok}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="etl/sample_data/legacy")
    ap.add_argument("--out", default="etl/sample_output")
    a = ap.parse_args()
    res = run(Path(a.source), Path(a.out))
    print(res["dq"].groupby(["object", "severity"]).size().to_string())
    print(res["recon"].to_string(index=False))
    print("LOAD GATE:", "OPEN – ready for staging load" if res["gate_ok"] else "CLOSED – reconciliation failed")
