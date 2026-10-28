-- Migration control database (Azure SQL) – object catalogue, value mappings, run log, DQ and reconciliation results.
-- Deployed once per environment; Power BI "Migration Cockpit dashboard" reads the etl.* tables.

CREATE SCHEMA etl;
GO
CREATE SCHEMA map;
GO

CREATE TABLE etl.migration_object (
    object_name      VARCHAR(40)   NOT NULL PRIMARY KEY,   -- bronze/silver folder name
    load_order       INT           NOT NULL,               -- migration sequence (docs/10)
    sap_object       VARCHAR(120)  NOT NULL,               -- Migration Cockpit migration object
    source_query     NVARCHAR(MAX) NULL,                   -- extract query against the legacy database (NULL = derived object)
    gold_object      VARCHAR(40)   NULL,                   -- gold dataset loaded to HANA staging (NULL = source only)
    blocking_dq      BIT           NOT NULL DEFAULT 1,     -- ERROR findings stop the load
    data_owner       VARCHAR(80)   NULL,
    enabled          BIT           NOT NULL DEFAULT 1
);

CREATE TABLE etl.run_log (
    id            BIGINT IDENTITY PRIMARY KEY,
    run_id        VARCHAR(40)  NOT NULL,                   -- MOCK1, MOCK2, MOCK3, CUTOVER
    step          VARCHAR(80)  NOT NULL,
    status        VARCHAR(40)  NOT NULL,
    pipeline_run  VARCHAR(80)  NULL,
    logged_at     DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE etl.dq_result (
    id        BIGINT IDENTITY PRIMARY KEY,
    run_id    VARCHAR(40)   NOT NULL,
    [object]  VARCHAR(40)   NOT NULL,
    [key]     VARCHAR(120)  NOT NULL,
    [rule]    VARCHAR(60)   NOT NULL,
    severity  VARCHAR(10)   NOT NULL CHECK (severity IN ('ERROR', 'WARNING')),
    message   NVARCHAR(400) NULL,
    resolved_by VARCHAR(80) NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX ix_dq_run ON etl.dq_result (run_id, [object], severity);

CREATE TABLE etl.recon_result (
    id         BIGINT IDENTITY PRIMARY KEY,
    run_id     VARCHAR(40)  NOT NULL,
    [object]   VARCHAR(40)  NOT NULL,
    [check]    VARCHAR(200) NOT NULL,
    expected   DECIMAL(19,2) NULL,
    actual     DECIMAL(19,2) NULL,
    difference DECIMAL(19,2) NULL,
    status     VARCHAR(4)   NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

-- Value mappings maintained by data owners (exported to config/mapping_rules.yaml for each mock load)
CREATE TABLE map.value_mapping (
    mapping_type  VARCHAR(40)  NOT NULL,     -- MERCH_CATEGORY, GL_ACCOUNT, SITE_TYPE, PROFIT_CENTER ...
    legacy_value  VARCHAR(80)  NOT NULL,
    sap_value     VARCHAR(80)  NOT NULL,
    approved_by   VARCHAR(80)  NULL,
    approved_at   DATETIME2    NULL,
    PRIMARY KEY (mapping_type, legacy_value)
);
GO

CREATE PROCEDURE etl.usp_log_step @run_id VARCHAR(40), @step VARCHAR(80), @status VARCHAR(40), @pipeline_run VARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO etl.run_log (run_id, step, status, pipeline_run) VALUES (@run_id, @step, @status, @pipeline_run);
END;
GO

-- Readiness view used by the go / no-go: open ERRORs and failed reconciliations per run
CREATE VIEW etl.v_load_readiness AS
SELECT r.run_id,
       SUM(CASE WHEN d.severity = 'ERROR' AND d.resolved_by IS NULL THEN 1 ELSE 0 END) AS open_errors,
       SUM(CASE WHEN d.severity = 'WARNING' THEN 1 ELSE 0 END)                         AS warnings,
       (SELECT COUNT(*) FROM etl.recon_result x WHERE x.run_id = r.run_id AND x.status = 'FAIL') AS recon_failures
FROM (SELECT DISTINCT run_id FROM etl.run_log) r
LEFT JOIN etl.dq_result d ON d.run_id = r.run_id
GROUP BY r.run_id;
GO
