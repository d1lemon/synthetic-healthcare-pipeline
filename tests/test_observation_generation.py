from datetime import datetime, timedelta
import random

import pytest

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)


def test_default_observation_count():
    patients = generate_patients()
    assert len(generate_observations(patients)) == 1000


def test_reproducible_output():
    patients = generate_patients(count=2)
    assert generate_observations(patients) == generate_observations(
        patients
    )


def test_different_seeds_change_output():
    patients = generate_patients(count=2)
    assert generate_observations(patients, seed=42) != (
        generate_observations(patients, seed=43)
    )


def test_unique_observation_ids():
    records = generate_observations(generate_patients(count=5))
    identifiers = [record["observation_id"] for record in records]
    assert len(identifiers) == len(set(identifiers))


def test_patient_references_and_counts():
    patients = generate_patients(count=3)
    records = generate_observations(patients)
    expected_ids = {patient["patient_id"] for patient in patients}
    assert {record["patient_id"] for record in records} == expected_ids
    for patient_id in expected_ids:
        assert sum(
            record["patient_id"] == patient_id for record in records
        ) == 10


def test_measurement_units_and_synthetic_labels():
    expected_units = {
        "heart_rate": "beats/min",
        "body_temperature": "degC",
        "body_weight": "kg",
    }
    records = generate_observations(generate_patients(count=1))
    assert {record["source_code"] for record in records} == set(
        expected_units
    )
    for record in records:
        assert record["unit"] == expected_units[record["source_code"]]
        assert isinstance(record["value"], (int, float))
        assert record["status"] == "final"
        assert record["is_synthetic"] is True


def test_timestamps_are_utc():
    records = generate_observations(generate_patients(count=1))
    for record in records:
        parsed = datetime.fromisoformat(record["observed_at"])
        assert parsed.utcoffset() == timedelta(0)


def test_empty_patients():
    assert generate_observations([]) == []


def test_zero_observations():
    assert generate_observations(
        generate_patients(count=1), observations_per_patient=0
    ) == []


def test_negative_count_rejected():
    with pytest.raises(ValueError):
        generate_observations([], observations_per_patient=-1)


@pytest.mark.parametrize("count", [True, 1.5, "10", None])
def test_invalid_count_type(count):
    with pytest.raises(TypeError):
        generate_observations([], observations_per_patient=count)


@pytest.mark.parametrize("seed", [True, 1.5, "42", None])
def test_invalid_seed_type(seed):
    with pytest.raises(TypeError):
        generate_observations([], seed=seed)


def test_duplicate_patient_ids_rejected():
    patient = generate_patients(count=1)[0]
    with pytest.raises(ValueError):
        generate_observations([patient, patient.copy()])


def test_missing_patient_id_rejected():
    with pytest.raises(ValueError):
        generate_observations([{"is_synthetic": True}])


def test_unlabeled_patient_rejected():
    with pytest.raises(ValueError):
        generate_observations([{"patient_id": "syn-patient-0001"}])


def test_global_random_state_unchanged():
    before = random.getstate()
    generate_observations(generate_patients(count=1))
    assert random.getstate() == before
