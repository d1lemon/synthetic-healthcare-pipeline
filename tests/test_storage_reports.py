from contextlib import closing
import csv
import json

import pytest

from healthcare_pipeline.database import (
    connect_database, initialize_database,
)
from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import generate_observations
from healthcare_pipeline.ingest import ingest_batch
from healthcare_pipeline.reports import write_reports
from healthcare_pipeline.storage import store_batch


def test_storage_report_reconciles_inserted_skipped_and_rejected(tmp_path):
    patients = generate_patients(count=1)
    observation = generate_observations(
        patients, observations_per_patient=1
    )[0]

    with closing(connect_database(tmp_path / "test.sqlite3")) as conn:
        initialize_database(conn)
        initial = ingest_batch(patients, [observation])
        store_batch(conn, initial, "first-run")

        new_observation = {
            **observation,
            "observation_id": "syn-observation-000002",
        }
        invalid_observation = {
            **observation,
            "observation_id": "syn-observation-000003",
            "value": "invalid",
        }
        batch = ingest_batch(
            patients,
            [observation, new_observation, invalid_observation],
        )
        stored = store_batch(conn, batch, "second-run")

    summary = stored["summary"]
    assert summary["input_total"] == 4
    assert summary["accepted_total"] == 1
    assert summary["skipped_total"] == 2
    assert summary["rejected_total"] == 1

    paths = write_reports(stored, tmp_path / "reports", "second-run")
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["summary"] == summary
    assert payload["run_id"] == stored["run_id"]

    with paths["csv"].open(encoding="utf-8", newline="") as handle:
        issues = list(csv.DictReader(handle))
    assert len(issues) == 1
    assert issues[0]["rule_id"] == "OBSERVATION_VALIDATION"

    markdown = paths["markdown"].read_text(encoding="utf-8")
    assert "Accepted total: 1" in markdown
    assert "Skipped total: 2" in markdown
    assert "Rejected total: 1" in markdown


def test_incorrect_skipped_summary_is_rejected(tmp_path):
    result = {
        "summary": {
            "input_total": 1,
            "accepted_total": 0,
            "rejected_total": 0,
            "skipped_total": 0,
        },
        "outcomes": [{
            "resource_type": "Patient",
            "input_index": 0,
            "record_id": "syn-patient-0001",
            "status": "skipped",
            "issues": [],
        }],
    }
    with pytest.raises(ValueError):
        write_reports(result, tmp_path / "reports", "invalid-summary")
    assert not (tmp_path / "reports").exists()
