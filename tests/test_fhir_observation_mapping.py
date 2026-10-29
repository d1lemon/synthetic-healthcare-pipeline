from copy import deepcopy
import json

import pytest

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.map_observation import observation_to_fhir


@pytest.fixture
def observation():
    return generate_observations(
        generate_patients(count=1), observations_per_patient=1
    )[0]


@pytest.mark.parametrize("source_code,unit,loinc,ucum", [
    ("heart_rate", "beats/min", "8867-4", "/min"),
    ("body_temperature", "degC", "8310-5", "Cel"),
    ("body_weight", "kg", "29463-7", "kg"),
])
def test_measurement_terminology(
    observation, source_code, unit, loinc, ucum
):
    observation.update(source_code=source_code, unit=unit)
    resource, _ = observation_to_fhir(observation)
    coding = resource["code"]["coding"][0]
    assert coding["system"] == "http://loinc.org"
    assert coding["code"] == loinc
    assert resource["valueQuantity"]["system"] == (
        "http://unitsofmeasure.org"
    )
    assert resource["valueQuantity"]["code"] == ucum


def test_common_fields(observation):
    resource, _ = observation_to_fhir(observation)
    assert resource["resourceType"] == "Observation"
    assert resource["id"] == observation["observation_id"]
    assert resource["status"] == "final"
    assert resource["subject"]["reference"] == (
        f"Patient/{observation['patient_id']}"
    )
    assert resource["category"][0]["coding"][0]["code"] == (
        "vital-signs"
    )
    assert resource["valueQuantity"]["value"] == observation["value"]


def test_fahrenheit_is_normalized_before_mapping(observation):
    observation.update(
        source_code="body_temperature", value=98.6, unit="degF"
    )
    resource, audit = observation_to_fhir(observation)
    assert resource["valueQuantity"]["value"] == pytest.approx(37.0)
    assert resource["valueQuantity"]["code"] == "Cel"
    assert audit["original"]["unit"] == "degF"
    assert audit["unit_converted"] is True


def test_pounds_are_normalized_before_mapping(observation):
    observation.update(
        source_code="body_weight", value=100.0, unit="lb"
    )
    resource, audit = observation_to_fhir(observation)
    assert resource["valueQuantity"]["value"] == pytest.approx(
        45.359237
    )
    assert resource["valueQuantity"]["code"] == "kg"
    assert audit["original"]["unit"] == "lb"


def test_timestamp_is_mapped_in_utc(observation):
    observation["observed_at"] = "2026-01-01T12:00:00-05:00"
    resource, _ = observation_to_fhir(observation)
    assert resource["effectiveDateTime"] == (
        "2026-01-01T17:00:00+00:00"
    )


def test_source_is_unchanged(observation):
    before = deepcopy(observation)
    observation_to_fhir(observation)
    assert observation == before


def test_resource_and_audit_are_json_serializable(observation):
    resource, audit = observation_to_fhir(observation)
    for item in (resource, audit):
        assert json.loads(json.dumps(item)) == item


def test_internal_fields_and_audit_are_not_in_resource(observation):
    resource, _ = observation_to_fhir(observation)
    for field in (
        "is_synthetic", "source_code", "patient_id", "audit"
    ):
        assert field not in resource
    assert "dataAbsentReason" not in resource


def test_all_generated_observations_map_with_resolved_references():
    patients = generate_patients(count=100)
    references = {
        f"Patient/{patient['patient_id']}" for patient in patients
    }
    source_records = generate_observations(patients)
    resources = [
        observation_to_fhir(source)[0] for source in source_records
    ]
    assert len(resources) == 1000
    assert len({resource["id"] for resource in resources}) == 1000
    assert all(
        resource["subject"]["reference"] in references
        for resource in resources
    )


def test_unsupported_unit_rejected(observation):
    observation["unit"] = "unknown"
    with pytest.raises(ValueError):
        observation_to_fhir(observation)
