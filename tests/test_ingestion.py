from copy import deepcopy
import json

import pytest

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.ingest import ingest_batch


def test_clean_batch():
    patients = generate_patients()
    observations = generate_observations(patients)
    result = ingest_batch(patients, observations)
    summary = result["summary"]
    assert summary["input_total"] == 1100
    assert summary["accepted_total"] == 1100
    assert summary["rejected_total"] == 0
    assert len(result["normalization_audits"]) == 1000
    assert len(result["outcomes"]) == 1100
    assert summary["independent_fhir_validation"] == "not_run"


def test_duplicate_patients():
    patient = generate_patients(count=1)[0]
    result = ingest_batch([patient, deepcopy(patient)], [])
    assert result["summary"]["accepted_patients"] == 1
    assert result["outcomes"][1]["issues"][0]["rule_id"] == (
        "DUPLICATE_PATIENT_ID"
    )


def test_duplicate_observations():
    patients = generate_patients(count=1)
    observation = generate_observations(
        patients, observations_per_patient=1
    )[0]
    result = ingest_batch(
        patients, [observation, deepcopy(observation)]
    )
    assert result["summary"]["accepted_observations"] == 1
    assert result["outcomes"][-1]["issues"][0]["rule_id"] == (
        "DUPLICATE_OBSERVATION_ID"
    )


def test_unknown_patient():
    observation = generate_observations(
        generate_patients(count=1), observations_per_patient=1
    )[0]
    result = ingest_batch([], [observation])
    assert result["outcomes"][0]["issues"][0]["rule_id"] == (
        "UNKNOWN_PATIENT"
    )


def test_rejected_patient_cannot_receive_observations():
    patients = generate_patients(count=1)
    observations = generate_observations(
        patients, observations_per_patient=1
    )
    patients[0]["birth_date"] = "invalid"
    result = ingest_batch(patients, observations)
    assert result["summary"]["accepted_total"] == 0
    assert result["summary"]["rejected_total"] == 2
    assert result["outcomes"][1]["issues"][0]["rule_id"] == (
        "UNKNOWN_PATIENT"
    )


def test_invalid_record_does_not_reserve_id():
    patient = generate_patients(count=1)[0]
    invalid = {**patient, "birth_date": "invalid"}
    result = ingest_batch([invalid, patient], [])
    assert result["summary"]["accepted_patients"] == 1
    assert [item["status"] for item in result["outcomes"]] == [
        "rejected", "accepted"
    ]


def test_mixed_input_has_one_outcome_per_record():
    patients = generate_patients(count=1)
    observation = generate_observations(
        patients, observations_per_patient=1
    )[0]
    invalid = {**observation, "value": "not-numeric"}
    result = ingest_batch(
        [*patients, None], [observation, invalid, "invalid"]
    )
    summary = result["summary"]
    assert summary["input_total"] == 5
    assert summary["accepted_total"] == 2
    assert summary["rejected_total"] == 3
    assert len(result["outcomes"]) == 5
    assert [
        item["input_index"]
        for item in result["outcomes"]
        if item["resource_type"] == "Observation"
    ] == [0, 1, 2]


def test_inputs_unchanged_and_output_serializable():
    patients = generate_patients(count=1)
    observations = generate_observations(
        patients, observations_per_patient=1
    )
    before = deepcopy((patients, observations))
    result = ingest_batch(patients, observations)
    assert (patients, observations) == before
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_empty_batch():
    result = ingest_batch([], [])
    assert result["summary"]["input_total"] == 0
    assert result["outcomes"] == []


def test_invalid_batch_container():
    with pytest.raises(TypeError):
        ingest_batch({}, [])
