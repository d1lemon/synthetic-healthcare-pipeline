from contextlib import closing

import pytest

from healthcare_pipeline.database import (
    connect_database, initialize_database,
)
from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.ingest import ingest_batch
from healthcare_pipeline.repository import (
    get_patient, get_observation, get_run_summary,
    list_patients, list_observations,
)
from healthcare_pipeline.storage import store_batch


@pytest.fixture
def populated_database(tmp_path):
    with closing(connect_database(tmp_path / "queries.sqlite3")) as conn:
        initialize_database(conn)
        patients = generate_patients(count=3)
        observations = generate_observations(
            patients, observations_per_patient=3
        )
        batch = ingest_batch(patients, observations)
        store_batch(conn, batch, "query-test-run")
        yield conn, batch


def test_get_patient(populated_database):
    conn, batch = populated_database
    assert get_patient(conn, "syn-patient-0001") == batch["patients"][0]


def test_get_observation(populated_database):
    conn, batch = populated_database
    assert get_observation(conn, "syn-observation-000001") == (
        batch["observations"][0]
    )


def test_missing_records_return_none(populated_database):
    conn, _ = populated_database
    assert get_patient(conn, "missing") is None
    assert get_observation(conn, "missing") is None
    assert get_run_summary(conn, "missing") is None


def test_patient_pagination(populated_database):
    conn, _ = populated_database
    first = list_patients(conn, limit=2, offset=0)
    second = list_patients(conn, limit=2, offset=2)
    assert first["total"] == second["total"] == 3
    assert [item["id"] for item in first["items"]] == [
        "syn-patient-0001", "syn-patient-0002"
    ]
    assert [item["id"] for item in second["items"]] == [
        "syn-patient-0003"
    ]


def test_observation_filter_and_pagination(populated_database):
    conn, _ = populated_database
    result = list_observations(
        conn, patient_id="syn-patient-0002", limit=2, offset=1
    )
    assert result["total"] == 3
    assert len(result["items"]) == 2
    assert all(
        item["subject"]["reference"] == "Patient/syn-patient-0002"
        for item in result["items"]
    )


def test_unfiltered_observation_listing(populated_database):
    conn, _ = populated_database
    result = list_observations(conn, limit=100)
    assert result["total"] == 9
    assert len(result["items"]) == 9


def test_unknown_patient_filter_returns_empty_list(populated_database):
    conn, _ = populated_database
    result = list_observations(conn, patient_id="syn-patient-9999")
    assert result["total"] == 0
    assert result["items"] == []


def test_offset_beyond_end(populated_database):
    conn, _ = populated_database
    result = list_patients(conn, offset=100)
    assert result["total"] == 3
    assert result["items"] == []


def test_run_summary(populated_database):
    conn, _ = populated_database
    result = get_run_summary(conn, "query-test-run")
    assert result["run_id"] == "query-test-run"
    assert result["started_at"]
    assert result["summary"]["accepted_total"] == 12


def test_id_input_is_used_as_a_literal_value(populated_database):
    conn, _ = populated_database
    assert get_patient(conn, "' OR 1=1 --") is None
    assert list_observations(
        conn, patient_id="' OR 1=1 --"
    )["total"] == 0
    assert list_patients(conn)["total"] == 3


@pytest.mark.parametrize("limit,offset,error", [
    (0, 0, ValueError),
    (101, 0, ValueError),
    (20, -1, ValueError),
    (True, 0, TypeError),
    (20, False, TypeError),
    ("20", 0, TypeError),
])
def test_invalid_pagination(
    populated_database, limit, offset, error
):
    conn, _ = populated_database
    with pytest.raises(error):
        list_patients(conn, limit=limit, offset=offset)
    with pytest.raises(error):
        list_observations(conn, limit=limit, offset=offset)
