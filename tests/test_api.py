from contextlib import closing
import sqlite3

from fastapi.testclient import TestClient
import pytest

from healthcare_pipeline.api import create_app
from healthcare_pipeline.database import (
    connect_database, initialize_database,
)
from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.ingest import ingest_batch
from healthcare_pipeline.storage import store_batch


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "api.sqlite3"
    with closing(connect_database(path)) as connection:
        initialize_database(connection)
        patients = generate_patients(count=3)
        observations = generate_observations(
            patients, observations_per_patient=3
        )
        store_batch(
            connection,
            ingest_batch(patients, observations),
            "api-test-run",
        )
    with TestClient(create_app(path)) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["dataset"] == "synthetic"


def test_patient_lookup(client):
    response = client.get("/patients/syn-patient-0001")
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Patient"
    assert response.json()["id"] == "syn-patient-0001"


def test_observation_lookup(client):
    response = client.get("/observations/syn-observation-000001")
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Observation"


@pytest.mark.parametrize("endpoint", [
    "/patients/missing",
    "/observations/missing",
    "/reports/missing",
])
def test_missing_resource(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 404
    assert "detail" in response.json()


def test_patient_pagination(client):
    response = client.get(
        "/patients", params={"limit": 2, "offset": 1}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [item["id"] for item in payload["items"]] == [
        "syn-patient-0002", "syn-patient-0003"
    ]


def test_observation_filter(client):
    response = client.get(
        "/observations",
        params={"patient_id": "syn-patient-0002", "limit": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["items"]) == 2
    assert all(
        item["subject"]["reference"] == "Patient/syn-patient-0002"
        for item in payload["items"]
    )


def test_unknown_patient_filter(client):
    response = client.get(
        "/observations", params={"patient_id": "missing"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.parametrize("endpoint", ["/patients", "/observations"])
@pytest.mark.parametrize("parameters", [
    {"limit": 0},
    {"limit": 101},
    {"offset": -1},
    {"limit": "not-an-integer"},
])
def test_invalid_pagination(client, endpoint, parameters):
    response = client.get(endpoint, params=parameters)
    assert response.status_code == 422


def test_run_summary(client):
    response = client.get("/reports/api-test-run")
    assert response.status_code == 200
    assert response.json()["summary"]["accepted_total"] == 12


def test_write_method_not_exposed(client):
    assert client.post("/patients", json={}).status_code == 405


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/observations/{observation_id}" in response.json()["paths"]


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError):
        create_app(path)
    assert not path.exists()
