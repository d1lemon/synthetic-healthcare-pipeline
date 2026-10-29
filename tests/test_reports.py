import csv
import json

import pytest

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.ingest import ingest_batch
from healthcare_pipeline.reports import write_reports


def test_reports_contain_reconciled_results(tmp_path):
    patients = generate_patients(count=1)
    observation = generate_observations(
        patients, observations_per_patient=1
    )[0]
    invalid = {**observation, "value": "invalid"}
    result = ingest_batch(patients, [observation, invalid])
    paths = write_reports(result, tmp_path, "test-run")

    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["summary"]["input_total"] == 3
    assert payload["summary"]["accepted_total"] == 2
    assert payload["summary"]["rejected_total"] == 1
    assert payload["issue_counts_by_rule"] == {
        "OBSERVATION_VALIDATION": 1
    }

    with paths["csv"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["input_index"] == "1"

    text = paths["markdown"].read_text(encoding="utf-8")
    assert "entirely synthetic" in text
    assert "Independent FHIR validation: not_run" in text


def test_empty_batch_writes_header_only_issue_csv(tmp_path):
    paths = write_reports(ingest_batch([], []), tmp_path, "empty")
    with paths["csv"].open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert list(reader) == []


def test_report_overwrite_rejected(tmp_path):
    result = ingest_batch([], [])
    paths = write_reports(result, tmp_path, "same-run")
    before = paths["json"].read_bytes()
    with pytest.raises(FileExistsError):
        write_reports(result, tmp_path, "same-run")
    assert paths["json"].read_bytes() == before


@pytest.mark.parametrize("run_id", [
    "", "../outside", "has space", "x" * 65
])
def test_unsafe_run_id_rejected(tmp_path, run_id):
    with pytest.raises(ValueError):
        write_reports(ingest_batch([], []), tmp_path, run_id)


def test_inconsistent_summary_rejected(tmp_path):
    result = ingest_batch([], [])
    result["summary"]["accepted_total"] = 1
    with pytest.raises(ValueError):
        write_reports(result, tmp_path, "bad-summary")
    assert list(tmp_path.iterdir()) == []
