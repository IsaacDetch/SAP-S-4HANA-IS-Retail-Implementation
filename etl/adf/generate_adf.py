"""Generate the Azure Data Factory JSON (linked services, datasets, pipelines) for the migration.

The JSON follows the ADF Git-integration layout (linkedService/, dataset/, pipeline/) so the folder can be
connected to a Data Factory as its repository or deployed with ARM templates exported from ADF.
Run: python etl/adf/generate_adf.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def save(kind: str, name: str, props: dict) -> None:
    (ROOT / kind).mkdir(exist_ok=True)
    with open(ROOT / kind / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "properties": props}, f, indent=2)
        f.write("\n")


kv = {"type": "LinkedServiceReference", "referenceName": "ls_keyvault"}
secret = lambda name: {"type": "AzureKeyVaultSecret", "store": kv, "secretName": name}
shir = {"referenceName": "shir-onprem", "type": "IntegrationRuntimeReference"}

# ---------------- Linked services ----------------
save("linkedService", "ls_keyvault", {"type": "AzureKeyVault", "typeProperties": {"baseUrl": "https://@{linkedService().vaultName}.vault.azure.net/"},
                                      "parameters": {"vaultName": {"type": "String", "defaultValue": "kv-retail-mig-dev"}}})
save("linkedService", "ls_legacy_sqlserver", {"type": "SqlServer", "connectVia": shir, "description": "Legacy merchandising & finance database (on-premises)",
                                              "typeProperties": {"connectionString": secret("legacy-sql-connection")}})
save("linkedService", "ls_legacy_files", {"type": "FileServer", "connectVia": shir, "description": "Legacy POS back-office and vendor extracts (CSV)",
                                          "typeProperties": {"host": "\\\\legacy-fs01\\exports", "userId": "svc_migration", "password": secret("legacy-fs-password")}})
save("linkedService", "ls_adls", {"type": "AzureBlobFS", "description": "Data lake – bronze / silver / gold (managed identity)",
                                  "typeProperties": {"url": "https://@{linkedService().storageAccount}.dfs.core.windows.net"},
                                  "parameters": {"storageAccount": {"type": "String", "defaultValue": "stretailmigdev"}}})
save("linkedService", "ls_sql_control", {"type": "AzureSqlDatabase", "description": "Migration control DB: object catalogue, mappings, run log, DQ & reconciliation",
                                         "typeProperties": {"connectionString": secret("sql-control-connection")}})
save("linkedService", "ls_databricks", {"type": "AzureDatabricks", "typeProperties": {"domain": "https://@{linkedService().workspaceUrl}", "authentication": "MSI",
                                        "workspaceResourceId": "@{linkedService().workspaceResourceId}", "existingClusterId": "@{linkedService().clusterId}"},
                                        "parameters": {"workspaceUrl": {"type": "String"}, "workspaceResourceId": {"type": "String"}, "clusterId": {"type": "String"}}})
save("linkedService", "ls_hana_staging_odbc", {"type": "Odbc", "connectVia": shir, "description": "Alternative load route: SAP HANA staging schema via ODBC sink on the self-hosted IR (HANA client installed)",
                                               "typeProperties": {"connectionString": secret("hana-staging-odbc"), "authenticationType": "Basic", "userName": "MIG_LOADER", "password": secret("hana-staging-password")}})
save("linkedService", "ls_s4_odata", {"type": "OData", "description": "S/4HANA OData / CDS services for post-load reconciliation extracts",
                                      "typeProperties": {"url": "https://@{linkedService().s4Host}/sap/opu/odata/sap/", "authenticationType": "Basic", "userName": "MIG_RECON", "password": secret("s4-recon-password")},
                                      "parameters": {"s4Host": {"type": "String"}}})

# ---------------- Datasets ----------------
save("dataset", "ds_legacy_sql_query", {"linkedServiceName": {"referenceName": "ls_legacy_sqlserver", "type": "LinkedServiceReference"}, "type": "SqlServerTable", "typeProperties": {}})
save("dataset", "ds_adls_parquet", {"linkedServiceName": {"referenceName": "ls_adls", "type": "LinkedServiceReference"},
                                    "parameters": {"container": {"type": "String"}, "folder": {"type": "String"}},
                                    "type": "Parquet", "typeProperties": {"location": {"type": "AzureBlobFSLocation", "fileSystem": "@dataset().container", "folderPath": "@dataset().folder"}, "compressionCodec": "snappy"}})
save("dataset", "ds_sql_control", {"linkedServiceName": {"referenceName": "ls_sql_control", "type": "LinkedServiceReference"}, "type": "AzureSqlTable",
                                   "typeProperties": {"schema": "etl", "table": "migration_object"}})
save("dataset", "ds_s4_odata", {"linkedServiceName": {"referenceName": "ls_s4_odata", "type": "LinkedServiceReference"}, "parameters": {"path": {"type": "String"}},
                                "type": "ODataResource", "typeProperties": {"path": "@dataset().path"}})

nb = lambda name, path, params, depends=None: {
    "name": name, "type": "DatabricksNotebook", "dependsOn": depends or [],
    "policy": {"timeout": "0.04:00:00", "retry": 1, "retryIntervalInSeconds": 120},
    "linkedServiceName": {"referenceName": "ls_databricks", "type": "LinkedServiceReference"},
    "typeProperties": {"notebookPath": path, "baseParameters": params}}
after = lambda *acts: [{"activity": a, "dependencyConditions": ["Succeeded"]} for a in acts]
log = lambda name, status, depends: {"name": name, "type": "SqlServerStoredProcedure", "dependsOn": depends,
                                     "linkedServiceName": {"referenceName": "ls_sql_control", "type": "LinkedServiceReference"},
                                     "typeProperties": {"storedProcedureName": "etl.usp_log_step", "storedProcedureParameters": {
                                         "run_id": {"value": "@pipeline().parameters.run_id", "type": "String"}, "step": {"value": name, "type": "String"},
                                         "status": {"value": status, "type": "String"}, "pipeline_run": {"value": "@pipeline().RunId", "type": "String"}}}}

# ---------------- Pipelines ----------------
save("pipeline", "pl_10_extract_legacy", {
    "description": "Extract every enabled legacy object (query from the control DB) to bronze Parquet, partitioned by run_id.",
    "parameters": {"run_id": {"type": "String"}},
    "activities": [
        {"name": "Lookup objects", "type": "Lookup", "typeProperties": {
            "source": {"type": "AzureSqlSource", "sqlReaderQuery": "SELECT object_name, source_query FROM etl.migration_object WHERE enabled = 1 AND source_query IS NOT NULL ORDER BY load_order"},
            "dataset": {"referenceName": "ds_sql_control", "type": "DatasetReference"}, "firstRowOnly": False}},
        {"name": "For each object", "type": "ForEach", "dependsOn": after("Lookup objects"), "typeProperties": {
            "items": {"value": "@activity('Lookup objects').output.value", "type": "Expression"}, "isSequential": False, "batchCount": 4,
            "activities": [{"name": "Copy to bronze", "type": "Copy", "policy": {"timeout": "0.02:00:00", "retry": 2},
                            "inputs": [{"referenceName": "ds_legacy_sql_query", "type": "DatasetReference"}],
                            "outputs": [{"referenceName": "ds_adls_parquet", "type": "DatasetReference", "parameters": {
                                "container": "bronze", "folder": {"value": "@concat(item().object_name, '/run_id=', pipeline().parameters.run_id)", "type": "Expression"}}}],
                            "typeProperties": {"source": {"type": "SqlServerSource", "sqlReaderQuery": {"value": "@item().source_query", "type": "Expression"}, "queryTimeout": "02:00:00"},
                                               "sink": {"type": "ParquetSink"}, "enableStaging": False}}]}},
        log("log_extract", "EXTRACTED", after("For each object"))]})

save("pipeline", "pl_20_transform", {
    "description": "Bronze -> silver -> gold in Databricks; fail the run if blocking DQ errors or reconciliation failures exist.",
    "parameters": {"run_id": {"type": "String"}, "posting_date": {"type": "String"}, "price_valid_from": {"type": "String"}, "allow_dq_errors": {"type": "Bool", "defaultValue": False}},
    "activities": [
        {"name": "Silver per object", "type": "ForEach", "typeProperties": {
            "items": {"value": "@createArray('stores','vendors','items','onhand','trial_balance')", "type": "Expression"}, "isSequential": False,
            "activities": [nb("Bronze to silver", "/Shared/migration/01_bronze_to_silver", {"run_id": "@pipeline().parameters.run_id", "object": "@item()"})]}},
        nb("Silver to gold", "/Shared/migration/02_silver_to_gold", {"run_id": "@pipeline().parameters.run_id", "posting_date": "@pipeline().parameters.posting_date",
                                                                     "price_valid_from": "@pipeline().parameters.price_valid_from"}, after("Silver per object")),
        {"name": "DQ gate", "type": "IfCondition", "dependsOn": after("Silver to gold"), "typeProperties": {
            "expression": {"value": "@or(pipeline().parameters.allow_dq_errors, and(equals(json(activity('Silver to gold').output.runOutput).recon_failed, 0), equals(json(activity('Silver to gold').output.runOutput).dq_errors, 0)))", "type": "Expression"},
            "ifFalseActivities": [{"name": "Stop – DQ or reconciliation failed", "type": "Fail", "typeProperties": {
                "message": "Data-quality errors or reconciliation failures – see etl.dq_result / etl.recon_result and the Power BI migration dashboard", "errorCode": "DQ_GATE"}}]}},
        log("log_transform", "TRANSFORMED", after("DQ gate"))]})

save("pipeline", "pl_30_load_hana_staging", {
    "description": "Load gold objects into the SAP Migration Cockpit staging tables in SAP HANA, in migration sequence.",
    "parameters": {"run_id": {"type": "String"}},
    "activities": [
        {"name": "Lookup load order", "type": "Lookup", "typeProperties": {
            "source": {"type": "AzureSqlSource", "sqlReaderQuery": "SELECT gold_object FROM etl.migration_object WHERE enabled = 1 AND gold_object IS NOT NULL ORDER BY load_order"},
            "dataset": {"referenceName": "ds_sql_control", "type": "DatasetReference"}, "firstRowOnly": False}},
        {"name": "Load each object", "type": "ForEach", "dependsOn": after("Lookup load order"), "typeProperties": {
            "items": {"value": "@activity('Lookup load order').output.value", "type": "Expression"}, "isSequential": True,
            "activities": [nb("Gold to HANA staging", "/Shared/migration/03_load_hana_staging", {"object": "@item().gold_object", "run_id": "@pipeline().parameters.run_id"})]}},
        log("log_staging", "STAGED", after("Load each object"))]})

save("pipeline", "pl_40_reconcile", {
    "description": "After the Migration Cockpit transfer: extract control totals from S/4HANA (OData/CDS) and compare with gold.",
    "parameters": {"run_id": {"type": "String"}},
    "activities": [
        {"name": "Extract S/4 control totals", "type": "Copy", "inputs": [{"referenceName": "ds_s4_odata", "type": "DatasetReference", "parameters": {"path": "ZMIG_RECON_SRV/ControlTotals"}}],
         "outputs": [{"referenceName": "ds_adls_parquet", "type": "DatasetReference", "parameters": {"container": "bronze", "folder": {"value": "@concat('s4_extract/run_id=', pipeline().parameters.run_id)", "type": "Expression"}}}],
         "typeProperties": {"source": {"type": "ODataSource"}, "sink": {"type": "ParquetSink"}}},
        nb("Reconcile target", "/Shared/migration/04_reconcile_target", {"run_id": "@pipeline().parameters.run_id"}, after("Extract S/4 control totals")),
        log("log_reconcile", "RECONCILED", after("Reconcile target"))]})

save("pipeline", "pl_00_master_migration", {
    "description": "Orchestrates one migration run (mock load or cutover): extract -> transform + DQ gate -> load HANA staging. Reconciliation (pl_40) runs after the Migration Cockpit transfer.",
    "parameters": {"run_id": {"type": "String", "defaultValue": "MOCK1"}, "posting_date": {"type": "String", "defaultValue": "2026-06-30"},
                   "price_valid_from": {"type": "String", "defaultValue": "2026-07-01"}, "allow_dq_errors": {"type": "Bool", "defaultValue": False}},
    "activities": [
        log("log_start", "STARTED", []),
        {"name": "Extract", "type": "ExecutePipeline", "dependsOn": after("log_start"), "typeProperties": {"pipeline": {"referenceName": "pl_10_extract_legacy", "type": "PipelineReference"},
                                                                                                         "waitOnCompletion": True, "parameters": {"run_id": "@pipeline().parameters.run_id"}}},
        {"name": "Transform", "type": "ExecutePipeline", "dependsOn": after("Extract"), "typeProperties": {"pipeline": {"referenceName": "pl_20_transform", "type": "PipelineReference"}, "waitOnCompletion": True,
            "parameters": {"run_id": "@pipeline().parameters.run_id", "posting_date": "@pipeline().parameters.posting_date", "price_valid_from": "@pipeline().parameters.price_valid_from",
                           "allow_dq_errors": "@pipeline().parameters.allow_dq_errors"}}},
        {"name": "Load HANA staging", "type": "ExecutePipeline", "dependsOn": after("Transform"), "typeProperties": {"pipeline": {"referenceName": "pl_30_load_hana_staging", "type": "PipelineReference"},
                                                                                                                   "waitOnCompletion": True, "parameters": {"run_id": "@pipeline().parameters.run_id"}}},
        log("log_end", "READY_FOR_MIGRATION_COCKPIT", after("Load HANA staging"))]})
print("ADF JSON written")
