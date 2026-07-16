-- BOM Guardian AI — Snowflake provisioning (run as SYSADMIN unless noted)
-- Status: authored and syntax-reviewed; NOT yet executed against a live Snowflake
-- account (no credentials in this project). Deployment status: pending.

CREATE DATABASE IF NOT EXISTS BOM_GUARDIAN
  COMMENT = 'BOM Guardian AI - supply chain data quality platform';

USE DATABASE BOM_GUARDIAN;

-- Layered schemas (raw -> staging -> core -> quality -> marts)
CREATE SCHEMA IF NOT EXISTS RAW        COMMENT = 'Source data as received, immutable';
CREATE SCHEMA IF NOT EXISTS STAGING    COMMENT = 'Standardized, originals preserved';
CREATE SCHEMA IF NOT EXISTS CORE       COMMENT = 'Conformed dimensions and facts';
CREATE SCHEMA IF NOT EXISTS QUALITY    COMMENT = 'DQ rules, issues, scores, remediation';
CREATE SCHEMA IF NOT EXISTS MARTS      COMMENT = 'Analytics marts for BI';
CREATE SCHEMA IF NOT EXISTS GROUND_TRUTH
  COMMENT = 'Injected-defect labels; evaluation only, never joined to model inputs';
CREATE SCHEMA IF NOT EXISTS OPS        COMMENT = 'Load audit, batches, observability';
