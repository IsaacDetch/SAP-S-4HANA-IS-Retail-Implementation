# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze → Silver (standardise legacy extracts)
# MAGIC Reads the Parquet files that ADF (`pl_10_extract_legacy`) landed in `bronze/<object>/run_id=<run_id>/`,
# MAGIC trims and types columns, removes exact duplicates and writes Delta tables to `silver`.
# MAGIC Parameters come from ADF: `run_id`, `object`.

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("object", "items")
run_id, obj = dbutils.widgets.get("run_id"), dbutils.widgets.get("object")
storage = spark.conf.get("spark.migration.storage_account")          # set in the cluster policy
lake = f"abfss://{{}}@{storage}.dfs.core.windows.net"
bronze = lake.format("bronze") + f"/{obj}/run_id={run_id}"
silver = lake.format("silver") + f"/{obj}"

# COMMAND ----------
from pyspark.sql import functions as F

df = spark.read.parquet(bronze)
for c, t in df.dtypes:
    if t == "string":
        df = df.withColumn(c, F.trim(F.col(c)))
df = (df.dropDuplicates()
        .withColumn("_run_id", F.lit(run_id))
        .withColumn("_ingested_at", F.current_timestamp()))
numeric = {"items": ["unit_cost", "retail_price"], "onhand": ["qty_on_hand", "unit_cost"], "trial_balance": ["debit", "credit"]}.get(obj, [])
for c in numeric:
    df = df.withColumn(c, F.coalesce(F.col(c).cast("decimal(18,2)"), F.lit(0)))
(df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(silver))
dbutils.notebook.exit(str(df.count()))
