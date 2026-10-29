from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.models import PatientRecord, ObservationRecord


@pytest.fixture
def patient():
    return generate_patients(count=1)[0]


@pytest.fixture
def observation(patient):
    return generate_observations(
        [patient], observations_per_patient=1
    )[0]


def test_generated_patients_validate():
    records = generate_patients(count=100)
    validated = [PatientRecord.model_validate(record) for record in records]
    assert len(validated) == 100
    assert isinstance(validated[0].birth_date, date)


def test_generated_observations_validate():
    patients = generate_patients(count=100)
    records = generate_observations(patients)
    validated = [
        ObservationRecord.model_validate(record) for record in records
    ]
    assert len(validated) == 1000
    assert validated[0].observed_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("changes", [
    {"patient_id": "real-patient-1"},
    {"given_name": ""},
    {"family_name": "   "},
    {"birth_date": "not-a-date"},
    {"is_synthetic": False},
    {"is_synthetic": 1},
    {"unexpected_field": "example"},
])
def test_invalid_patient_rejected(patient, changes):
    with pytest.raises(ValidationError):
        PatientRecord.model_validate({**patient, **changes})


@pytest.mark.parametrize("changes", [
    {"observation_id": "observation-1"},
    {"patient_id": "patient-1"},
    {"source_code": "unsupported"},
    {"value": "64.0"},
    {"value": True},
    {"value": float("nan")},
    {"value": float("inf")},
    {"unit": "kg"},
    {"observed_at": "2026-01-01T12:00:00"},
    {"status": "unsupported"},
    {"is_synthetic": False},
    {"is_synthetic": 1},
    {"unexpected_field": "example"},
])
def test_invalid_observation_rejected(observation, changes):
    with pytest.raises(ValidationError):
        ObservationRecord.model_validate({**observation, **changes})


def test_missing_patient_field_rejected(patient):
    patient.pop("birth_date")
    with pytest.raises(ValidationError):
        PatientRecord.model_validate(patient)


def test_missing_observation_field_rejected(observation):
    observation.pop("value")
    with pytest.raises(ValidationError):
        ObservationRecord.model_validate(observation)


def test_models_round_trip_through_json(patient, observation):
    for model_type, source in (
        (PatientRecord, patient),
        (ObservationRecord, observation),
    ):
        original = model_type.model_validate(source)
        restored = model_type.model_validate_json(
            original.model_dump_json()
        )
        assert restored == original
