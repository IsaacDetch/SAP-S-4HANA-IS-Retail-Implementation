from pathlib import Path

import pandas as pd
import pytest

from retail_etl import gtin_check_digit, is_valid_gtin, load_rules, transform
from retail_etl.pipeline import run
from retail_etl.rules import profit_center
from retail_etl.staging import insert_sql, load_dataframe

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "legacy"
RULES = load_rules()


@pytest.mark.parametrize("code,ok", [("036000291452", True), ("036000291453", False), ("4006381333931", True), ("12345", False), ("", False), (None, False)])
def test_gtin(code, ok):
    assert is_valid_gtin(code) is ok


def test_check_digit_upc():
    assert gtin_check_digit("03600029145") == 2


def test_profit_center_derivation():
    assert profit_center("ST07", RULES) == "2107"
    assert profit_center("DC01", RULES) == "1100"
    with pytest.raises(KeyError):
        profit_center("XX99", RULES)


def test_site_categories():
    stores = pd.DataFrame([{"store_id": "st01", "store_name": "A", "store_type": "STORE", "street": "", "city": "", "state": "", "zip": "123", "country": "US", "open_date": "2020-01-01"},
                           {"store_id": "DC01", "store_name": "B", "store_type": "DC", "street": "", "city": "", "state": "", "zip": "91761", "country": "US", "open_date": "2015-01-01"}])
    gold, dq = transform.sites(stores, RULES)
    assert dq.empty
    assert dict(zip(gold.WERKS, gold.VLFKZ)) == {"ST01": "A", "DC01": "B"}
    assert gold.loc[gold.WERKS == "ST01", "PSTLZ"].item() == "00123"


def test_articles_generic_and_variants():
    items = pd.DataFrame([{"style": "TS-1", "style_desc": "Tee", "dept": "10", "class": "100", "color": "blk", "size": "m", "upc": "036000291452", "unit_cost": "8", "retail_price": "19.99", "vendor_id": "V1"},
                          {"style": "TS-1", "style_desc": "Tee", "dept": "10", "class": "100", "color": "blk", "size": "l", "upc": "036000291453", "unit_cost": "8", "retail_price": "19.99", "vendor_id": "V1"}])
    gold, dq = transform.articles(items, RULES)
    assert list(gold.ATTYP) == ["01", "02"]
    assert gold.iloc[1].MATNR == "TS-1-BLK-M" and gold.iloc[1].SATNR == "TS-1" and gold.iloc[1].MATKL == "11010"
    assert list(dq.rule) == ["INVALID_GTIN"]


def test_gl_balances_reroutes_inventory_and_detects_imbalance():
    tb = pd.DataFrame([{"legacy_account": "1400", "store_id": "", "debit": 100.0, "credit": 0.0}, {"legacy_account": "3000", "store_id": "", "debit": 0.0, "credit": 90.0}])
    gold, dq = transform.gl_balances(tb, RULES, "2026-06-30")
    assert gold.iloc[0].HKONT == transform.MIGRATION_CLEARING and gold.iloc[0].LEGACY_HKONT == "13400000"
    assert "TB_NOT_BALANCED" in set(dq.rule)


def test_full_sample_run(tmp_path):
    res = run(SAMPLE, tmp_path)
    assert res["gate_ok"], res["recon"]
    errors = res["dq"][res["dq"].severity == "ERROR"]
    assert set(errors.rule) >= {"INVALID_GTIN", "DUPLICATE_GTIN", "MC_UNMAPPED", "DUPLICATE_TAX_ID", "NEGATIVE_STOCK"}
    assert res["totals"]["article.variant"] == 9
    assert res["totals"]["inventory_balance.value"] == 15520.0
    assert (tmp_path / "gold_article.csv").exists()


class StubCursor:
    def __init__(self):
        self.sql, self.rows = [], []
    def execute(self, sql, params=None):
        self.sql.append(sql)
    def executemany(self, sql, rows):
        self.sql.append(sql); self.rows.extend(rows)


def test_staging_loader_truncates_and_inserts():
    cur = StubCursor()
    df = pd.DataFrame({"MATNR": ["A", "B"], "KBETR": [1.5, None]})
    n = load_dataframe(cur, "MIG", "/1LT/DS_TEST", df, batch_size=1)
    assert n == 2 and cur.sql[0] == 'TRUNCATE TABLE "MIG"."/1LT/DS_TEST"'
    assert cur.rows == [("A", 1.5), ("B", None)]
    assert insert_sql("MIG", "T", ["A"]) == 'INSERT INTO "MIG"."T" ("A") VALUES (?)'
