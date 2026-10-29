"""SQLite connection and schema for the synthetic pipeline."""

import sqlite3


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS ingestion_runs (
        run_id TEXT PRIMARY KEY NOT NULL,
        started_at TEXT NOT NULL,
        summary_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY NOT NULL,
        resource_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS observations (
        observation_id TEXT PRIMARY KEY NOT NULL,
        patient_id TEXT NOT NULL,
        code TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        resource_json TEXT NOT NULL,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_observations_patient
    ON observations(patient_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS record_outcomes (
        run_id TEXT NOT NULL,
        resource_type TEXT NOT NULL
            CHECK (resource_type IN ('Patient', 'Observation')),
        input_index INTEGER NOT NULL CHECK (input_index >= 0),
        record_id TEXT,
        status TEXT NOT NULL
            CHECK (status IN ('accepted', 'rejected', 'skipped')),
        issues_json TEXT NOT NULL,
        PRIMARY KEY (run_id, resource_type, input_index),
        FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS normalization_audits (
        run_id TEXT NOT NULL,
        observation_id TEXT NOT NULL,
        audit_json TEXT NOT NULL,
        PRIMARY KEY (run_id, observation_id),
        FOREIGN KEY (run_id) REFERENCES ingestion_runs(run_id),
        FOREIGN KEY (observation_id)
            REFERENCES observations(observation_id)
    )
    """,
)


def connect_database(path) -> sqlite3.Connection:
    """Open a connection with verified foreign-key enforcement."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        enabled = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]
        if enabled != 1:
            raise RuntimeError("Foreign-key enforcement is unavailable")
    except Exception:
        connection.close()
        raise
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create the initial schema outside any existing transaction."""
    if connection.in_transaction:
        raise RuntimeError(
            "Initialize the schema before starting a transaction"
        )
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Foreign-key enforcement must be enabled")

    with connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
