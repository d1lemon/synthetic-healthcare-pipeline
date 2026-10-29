from contextlib import closing
import sqlite3

import pytest

from healthcare_pipeline.database import (
    connect_database,
    initialize_database,
)


def test_schema_and_foreign_keys(tmp_path):
    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        tables = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert tables == {
            "patients", "observations", "ingestion_runs",
            "record_outcomes", "normalization_audits",
        }


def test_schema_initialization_is_repeatable(tmp_path):
    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        initialize_database(conn)
        assert list(conn.execute("PRAGMA foreign_key_check")) == []


def test_orphan_observation_is_rejected(tmp_path):
    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    """
                    INSERT INTO observations
                    (observation_id, patient_id, code,
                     observed_at, resource_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "syn-observation-000001",
                        "syn-patient-9999",
                        "8867-4",
                        "2026-01-01T00:00:00+00:00",
                        "{}",
                    ),
                )


def test_transaction_rolls_back_on_constraint_failure(tmp_path):
    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                conn.execute(
                    "INSERT INTO patients VALUES (?, ?)",
                    ("syn-patient-0001", "{}"),
                )
                conn.execute(
                    "INSERT INTO patients VALUES (?, ?)",
                    ("syn-patient-0001", "{}"),
                )
        assert conn.execute(
            "SELECT COUNT(*) FROM patients"
        ).fetchone()[0] == 0


def test_committed_record_survives_reconnection(tmp_path):
    path = tmp_path / "test.sqlite3"
    with closing(connect_database(path)) as conn:
        initialize_database(conn)
        with conn:
            conn.execute(
                "INSERT INTO patients VALUES (?, ?)",
                ("syn-patient-0001", "{}"),
            )

    with closing(connect_database(path)) as conn:
        assert conn.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0] == 1
        row = conn.execute(
            "SELECT patient_id FROM patients"
        ).fetchone()
        assert row["patient_id"] == "syn-patient-0001"


def test_schema_initialization_rejects_active_transaction(tmp_path):
    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        conn.execute(
            "INSERT INTO patients VALUES (?, ?)",
            ("syn-patient-0001", "{}"),
        )
        with pytest.raises(RuntimeError):
            initialize_database(conn)
        conn.rollback()
