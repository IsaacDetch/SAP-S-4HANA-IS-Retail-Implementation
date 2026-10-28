# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver → Gold (SAP staging layout) + data-quality gate
# MAGIC Applies the shared rules in `retail_etl.transform` (installed on the cluster as a wheel built from `etl/src`)
# MAGIC and writes gold Delta tables with SAP technical field names, plus DQ findings to Azure SQL (`etl.dq_result`).
# MAGIC Master data objects are transformed with pandas (volumes up to a few million rows);
# MAGIC inventory balances run per site partition with `applyInPandas` so they scale with the number of stores.
# MAGIC The notebook exits with the number of ERROR findings; ADF stops the load if it is not 0 for blocking objects.

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("posting_date", "2026-06-30")
dbutils.widgets.text("price_valid_from", "2026-07-01")
run_id = dbutils.widgets.get("run_id")
posting_date, valid_from = dbutils.widgets.get("posting_date"), dbutils.widgets.get("price_valid_from")
storage = spark.conf.get("spark.migration.storage_account")
lake = lambda zone, obj: f"abfss://{zone}@{storage}.dfs.core.windows.net/{obj}"

# COMMAND ----------
import pandas as pd
from pyspark.sql import functions as F
from retail_etl import load_rules, transform, reconcile

rules = load_rules("/Workspace/Shared/migration/config/mapping_rules.yaml")
read = lambda obj: spark.read.format("delta").load(lake("silver", obj)).drop("_run_id", "_ingested_at")
silver = {k: read(k).toPandas().astype(str) for k in ["stores", "vendors", "items"]}
tb = read("trial_balance").toPandas(); tb[["debit", "credit"]] = tb[["debit", "credit"]].astype(float)
silver["trial_balance"] = tb

gold, dqs = {}, []
gold["site"], d = transform.sites(silver["stores"], rules); dqs.append(d)
gold["supplier"], d = transform.suppliers(silver["vendors"], rules); dqs.append(d)
gold["article"], d = transform.articles(silver["items"], rules); dqs.append(d)
gold["sales_price"], d = transform.sales_prices(silver["items"], gold["article"], rules, valid_from); dqs.append(d)
gold["gl_balance"], d = transform.gl_balances(silver["trial_balance"], rules, posting_date); dqs.append(d)

# COMMAND ----------
# Inventory balances: distributed per site
art_b, site_b = sc.broadcast(gold["article"]), sc.broadcast(gold["site"])
inv_schema = "MATNR string, WERKS string, LGORT string, BWART string, ERFMG double, ERFME string, EXBWR double, WAERS string, BUDAT string"
dq_schema = "object string, key string, rule string, severity string, message string"

def inv_part(pdf: pd.DataFrame) -> pd.DataFrame:
    g, _ = transform.inventory_balances(pdf, art_b.value, site_b.value, rules, posting_date)
    return g if not g.empty else pd.DataFrame(columns=inv_schema.replace(" string", "").replace(" double", "").split(", "))

def inv_dq(pdf: pd.DataFrame) -> pd.DataFrame:
    _, d = transform.inventory_balances(pdf, art_b.value, site_b.value, rules, posting_date)
    return d

onhand = read("onhand").select(*[F.col(c).cast("string") for c in ["store_id", "upc", "qty_on_hand", "unit_cost"]])
inv_sdf = onhand.groupBy("store_id").applyInPandas(inv_part, inv_schema)
inv_dq_sdf = onhand.groupBy("store_id").applyInPandas(inv_dq, dq_schema)

# COMMAND ----------
for k, v in gold.items():
    spark.createDataFrame(v.astype(str)).write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(lake("gold", k))
inv_sdf.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(lake("gold", "inventory_balance"))
gold["inventory_balance"] = spark.read.format("delta").load(lake("gold", "inventory_balance")).toPandas()

dq = pd.concat([x for x in dqs if not x.empty] + [inv_dq_sdf.toPandas()], ignore_index=True)
dq["run_id"] = run_id
recon = pd.concat([reconcile.source_vs_gold(silver, gold, dq), reconcile.cross_object_checks(silver, gold, rules)], ignore_index=True)
recon["run_id"] = run_id

jdbc = dbutils.secrets.get("kv-migration", "sql-control-jdbc")       # Key Vault-backed secret scope
spark.createDataFrame(dq.astype(str)).write.jdbc(jdbc, "etl.dq_result", mode="append")
spark.createDataFrame(recon.astype(str)).write.jdbc(jdbc, "etl.recon_result", mode="append")

errors = int((dq["severity"] == "ERROR").sum()); failed = int((recon["status"] == "FAIL").sum())
dbutils.notebook.exit(f'{{"dq_errors": {errors}, "recon_failed": {failed}}}')
