# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Post-load reconciliation (gold vs SAP S/4HANA)
# MAGIC After the Migration Cockpit transfer, ADF (`pl_40_reconcile`) extracts control data from S/4HANA via
# MAGIC OData / CDS views into `bronze/s4_extract/` (e.g. sites, article counts by type, stock quantity & value
# MAGIC by site from the material stock CDS view, G/L balances from the trial balance view). This notebook
# MAGIC computes the same control totals and compares them with the gold totals. Results go to `etl.recon_result`
# MAGIC and the Power BI migration dashboard; any FAIL blocks the go / no-go criterion "data reconciled".

# COMMAND ----------
dbutils.widgets.text("run_id", "")
run_id = dbutils.widgets.get("run_id")
storage = spark.conf.get("spark.migration.storage_account")
lake = lambda zone, p: f"abfss://{zone}@{storage}.dfs.core.windows.net/{p}"

import pandas as pd
from retail_etl import reconcile

gold = {k: spark.read.format("delta").load(lake("gold", k)).toPandas() for k in ["site", "supplier", "article", "sales_price", "inventory_balance", "gl_balance"]}
for c in ("ERFMG", "EXBWR", "KBETR", "WRBTR"):
    for g in gold.values():
        if c in g:
            g[c] = g[c].astype(float)
expected = reconcile.control_totals(gold)

s4 = spark.read.parquet(lake("bronze", f"s4_extract/run_id={run_id}")).toPandas()   # columns: control_total, value
actual = dict(zip(s4["control_total"], s4["value"].astype(float)))
result = reconcile.compare_with_target(expected, actual)
result["run_id"] = run_id
spark.createDataFrame(result.astype(str)).write.jdbc(dbutils.secrets.get("kv-migration", "sql-control-jdbc"), "etl.recon_result", mode="append")
display(result)
dbutils.notebook.exit(str(int((result["status"] == "FAIL").sum())))
