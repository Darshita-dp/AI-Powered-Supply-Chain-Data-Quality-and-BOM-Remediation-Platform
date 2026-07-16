-- Compute warehouses. XS with aggressive auto-suspend keeps cost minimal.
-- Run as SYSADMIN. Not yet executed against a live account (status: pending).

CREATE WAREHOUSE IF NOT EXISTS BOMG_WH_XS
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Default warehouse for ingestion, dbt, and API queries';

CREATE WAREHOUSE IF NOT EXISTS BOMG_WH_ML
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Entity resolution / evaluation workloads';

-- Resource monitor guidance: attach a monitor with a modest monthly quota, e.g.
--   CREATE RESOURCE MONITOR BOMG_MONITOR WITH CREDIT_QUOTA = 10
--     TRIGGERS ON 90 PERCENT DO SUSPEND;
--   ALTER WAREHOUSE BOMG_WH_XS SET RESOURCE_MONITOR = BOMG_MONITOR;
-- (Requires ACCOUNTADMIN.)
