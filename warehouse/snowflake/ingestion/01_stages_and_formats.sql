-- Stages and file formats for CSV ingestion. Status: authored, not yet executed.

USE DATABASE BOM_GUARDIAN;
USE SCHEMA RAW;

CREATE FILE FORMAT IF NOT EXISTS BOMG_CSV_FORMAT
  TYPE = CSV
  PARSE_HEADER = TRUE
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('', 'NULL', 'None')
  EMPTY_FIELD_AS_NULL = TRUE
  COMMENT = 'Generator CSV output format';

-- Internal stage; swap for an external (S3/Azure) stage in a real deployment.
CREATE STAGE IF NOT EXISTS BOMG_LANDING
  FILE_FORMAT = BOMG_CSV_FORMAT
  COMMENT = 'Landing stage for synthetic ERP extracts';

-- Upload pattern (SnowSQL):
--   PUT file://data_generator/output/<profile>/*.csv @BOMG_LANDING/<profile>/ AUTO_COMPRESS=TRUE;
-- Load pattern (see tasks/01_load_tasks.sql for scheduled variant):
--   COPY INTO RAW.<TABLE> FROM @BOMG_LANDING/<profile>/<table>.csv.gz
--     FILE_FORMAT = (FORMAT_NAME = BOMG_CSV_FORMAT)
--     MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE ON_ERROR = 'CONTINUE';
