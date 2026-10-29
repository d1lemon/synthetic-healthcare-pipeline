from contextlib import closing
from copy import deepcopy
import json
import sqlite3

import pytest

from healthcare_pipeline.database import (
    connect_database, initialize_database,
)
from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.ingest import ingest_batch
from healthcare_pipeline.storage import (
    ResourceConflictError, store_batch,
)


@pytest.fixture
def connection(tmp_path):
    with closing(connect_database(tmp_path / "storage.sqlite3")) as conn:
        initialize_database(conn)
        yield conn


@pytest.fixture
def batch():
    patients = generate_patients(count=2)
    observations = generate_observations(
        patients, observations_per_patient=3
    )
    return ingest_batch(patients, observations)


def test_resources_and_audits_are_stored(connection, batch):
    result = store_batch(connection, batch, "run-1")
    assert result["summary"]["accepted_total"] == 8
    assert connection.execute(
        "SELECT COUNT(*) FROM patients"
    ).fetchone()[0] == 2
    assert connection.execute(
        "SELECT COUNT(*) FROM observations"
    ).fetchone()[0] == 6
    assert connection.execute(
        "SELECT COUNT(*) FROM normalization_audits"
    ).fetchone()[0] == 6
    assert connection.execute(
        "SELECT COUNT(*) FROM record_outcomes"
    ).fetchone()[0] == 8
    payload = connection.execute(
        "SELECT resource_json FROM patients ORDER BY patient_id"
    ).fetchone()[0]
    assert json.loads(payload) == batch["patients"][0]


def test_identical_resources_are_skipped(connection, batch):
    store_batch(connection, batch, "run-1")
    result = store_batch(connection, batch, "run-2")
    assert result["summary"]["accepted_total"] == 0
    assert result["summary"]["skipped_total"] == 8
    assert connection.execute(
        "SELECT COUNT(*) FROM observations"
    ).fetchone()[0] == 6
    assert connection.execute(
        "SELECT COUNT(*) FROM ingestion_runs"
    ).fetchone()[0] == 2


def test_conflict_rolls_back_earlier_insert(connection, batch):
    store_batch(connection, batch, "run-1")

    patients = generate_patients(count=3)
    observations = generate_observations(
        patients, observations_per_patient=3
    )
    changed = ingest_batch(patients, observations)
    changed["patients"].reverse()
    changed["observations"][0]["valueQuantity"]["value"] += 1

    with pytest.raises(ResourceConflictError):
        store_batch(connection, changed, "conflict-run")

    assert connection.execute(
        "SELECT COUNT(*) FROM patients"
    ).fetchone()[0] == 2
    assert connection.execute(
        "SELECT COUNT(*) FROM ingestion_runs WHERE run_id = ?",
        ("conflict-run",),
    ).fetchone()[0] == 0
    assert connection.in_transaction is False


def test_reused_run_id_is_rejected(connection, batch):
    store_batch(connection, batch, "run-1")
    with pytest.raises(sqlite3.IntegrityError):
        store_batch(connection, batch, "run-1")
    assert connection.execute(
        "SELECT COUNT(*) FROM ingestion_runs"
    ).fetchone()[0] == 1


def test_input_result_is_not_modified(connection, batch):
    before = deepcopy(batch)
    store_batch(connection, batch, "run-1")
    store_batch(connection, batch, "run-2")
    assert batch == before


def test_rejected_outcome_is_preserved(connection):
    batch = ingest_batch([None], [])
    result = store_batch(connection, batch, "rejected-run")
    assert result["summary"]["rejected_total"] == 1
    row = connection.execute(
        "SELECT status, issues_json FROM record_outcomes"
    ).fetchone()
    assert row["status"] == "rejected"
    assert json.loads(row["issues_json"])[0]["rule_id"] == "SOURCE_TYPE"
