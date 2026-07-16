"""Raw-layer ingestion with full load audit.

Every ingested row carries audit columns (batch, timestamps, hashes, sequence,
status). Idempotency is file-hash based: a file whose SHA-256 was already loaded
successfully is skipped. Rows failing basic contract checks (null primary key)
are diverted to ops.rejected_records instead of raw.

Ground-truth files are deliberately excluded: they are evaluation-only inputs
and are loaded into the isolated ground_truth schema via load_ground_truth().
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from bom_guardian.observability import get_logger
from bom_guardian.warehouse import LocalWarehouse

SCHEMA_VERSION = "1.0"

_AUDIT_DDL = {
    "load_batches": """
        CREATE TABLE IF NOT EXISTS ops.load_batches (
            batch_id VARCHAR, profile VARCHAR, started_at TIMESTAMP,
            finished_at TIMESTAMP, files_loaded INTEGER, files_skipped INTEGER,
            rows_loaded BIGINT, rows_rejected BIGINT, status VARCHAR
        )
    """,
    "load_files": """
        CREATE TABLE IF NOT EXISTS ops.load_files (
            batch_id VARCHAR, filename VARCHAR, file_hash VARCHAR,
            target_table VARCHAR, rows_loaded BIGINT, rows_rejected BIGINT,
            status VARCHAR, loaded_at TIMESTAMP
        )
    """,
    "rejected_records": """
        CREATE TABLE IF NOT EXISTS ops.rejected_records (
            batch_id VARCHAR, source_filename VARCHAR, target_table VARCHAR,
            record_seq BIGINT, reason VARCHAR, record_json VARCHAR,
            rejected_at TIMESTAMP
        )
    """,
}


class IngestionService:
    """Loads generator CSV output into the raw layer with audit and idempotency."""

    def __init__(self, warehouse: LocalWarehouse) -> None:
        self.wh = warehouse
        self._log = get_logger("ingestion")
        for ddl in _AUDIT_DDL.values():
            self.wh.execute(ddl)

    # ------------------------------------------------------------------
    def _already_loaded(self, file_hash: str) -> bool:
        df = self.wh.query(
            f"SELECT 1 FROM ops.load_files WHERE file_hash = '{file_hash}' "
            "AND status = 'LOADED' LIMIT 1"
        )
        return not df.empty

    @staticmethod
    def _row_hash(row: pd.Series) -> str:
        payload = "|".join("" if pd.isna(v) else str(v) for v in row)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def ingest_file(self, path: Path, batch_id: str, profile: str = "unknown") -> dict:
        """Ingest one CSV into raw.<stem>. Returns per-file stats."""
        table = path.stem
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        now = datetime.now(UTC)

        if self._already_loaded(file_hash):
            self._log.info("file_skipped_idempotent", file=path.name)
            self.wh.execute(
                "INSERT INTO ops.load_files VALUES "
                f"('{batch_id}', '{path.name}', '{file_hash}', 'raw.{table}', 0, 0, "
                f"'SKIPPED_DUPLICATE', '{now.isoformat()}')"
            )
            return {"table": table, "status": "SKIPPED_DUPLICATE", "loaded": 0, "rejected": 0}

        df = pd.read_csv(path)
        pk_col = df.columns[0]
        bad_mask = df[pk_col].isna()
        rejected = df[bad_mask]
        good = df[~bad_mask].copy()

        # audit columns
        good["_source_system_file"] = path.name
        good["_ingestion_batch_id"] = batch_id
        good["_ingested_at"] = now
        good["_file_hash"] = file_hash
        good["_schema_version"] = SCHEMA_VERSION
        good["_record_seq"] = range(1, len(good) + 1)
        good["_row_hash"] = good.apply(self._row_hash, axis=1)
        good["_load_status"] = "LOADED"

        self.wh.load_dataframe("raw", table, good, replace=not self._table_exists(table))

        for seq, (_, row) in enumerate(rejected.iterrows(), start=1):
            reason = f"null primary key ({pk_col})"
            record_json = row.to_json().replace("'", "''")
            self.wh.execute(
                "INSERT INTO ops.rejected_records VALUES "
                f"('{batch_id}', '{path.name}', 'raw.{table}', {seq}, "
                f"'{reason}', '{record_json}', '{now.isoformat()}')"
            )

        self.wh.execute(
            "INSERT INTO ops.load_files VALUES "
            f"('{batch_id}', '{path.name}', '{file_hash}', 'raw.{table}', "
            f"{len(good)}, {len(rejected)}, 'LOADED', '{now.isoformat()}')"
        )
        self._log.info(
            "file_loaded", file=path.name, table=table, rows=len(good), rejected=len(rejected)
        )
        return {"table": table, "status": "LOADED", "loaded": len(good), "rejected": len(rejected)}

    def _table_exists(self, table: str) -> bool:
        return table in self.wh.tables("raw")

    def ingest_directory(self, directory: Path, profile: str = "unknown") -> dict:
        """Ingest every CSV in a generator output directory (excluding ground truth)."""
        batch_id = f"BATCH-{uuid.uuid4().hex[:12]}"
        started = datetime.now(UTC)
        log = self._log.bind(batch_id=batch_id)
        files = sorted(p for p in directory.glob("*.csv"))
        stats = {"loaded_files": 0, "skipped_files": 0, "rows_loaded": 0, "rows_rejected": 0}
        for path in files:
            result = self.ingest_file(path, batch_id, profile)
            if result["status"] == "LOADED":
                stats["loaded_files"] += 1
            else:
                stats["skipped_files"] += 1
            stats["rows_loaded"] += result["loaded"]
            stats["rows_rejected"] += result["rejected"]

        finished = datetime.now(UTC)
        self.wh.execute(
            "INSERT INTO ops.load_batches VALUES "
            f"('{batch_id}', '{profile}', '{started.isoformat()}', '{finished.isoformat()}', "
            f"{stats['loaded_files']}, {stats['skipped_files']}, {stats['rows_loaded']}, "
            f"{stats['rows_rejected']}, 'COMPLETED')"
        )
        log.info("batch_complete", **stats)
        return {"batch_id": batch_id, **stats}

    def load_ground_truth(self, labels_csv: Path) -> int:
        """Load injected-defect labels into the isolated ground_truth schema."""
        df = pd.read_csv(labels_csv)
        return self.wh.load_dataframe("ground_truth", "labels", df)
