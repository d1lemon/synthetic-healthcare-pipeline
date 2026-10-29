from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.map_fhir import (
    FHIR_VERSION,
    patient_to_fhir,
)


@pytest.fixture
def patient():
    return generate_patients(count=1)[0]


def test_target_version():
    assert FHIR_VERSION == "4.0.1"


def test_patient_fields_are_mapped(patient):
    resource = patient_to_fhir(patient)
    assert resource == {
        "resourceType": "Patient",
        "id": patient["patient_id"],
        "name": [{
            "family": patient["family_name"],
            "given": [patient["given_name"]],
        }],
        "birthDate": patient["birth_date"],
    }


def test_all_generated_patients_map():
    patients = generate_patients(count=100)
    resources = [patient_to_fhir(patient) for patient in patients]
    assert len(resources) == 100
    assert len({resource["id"] for resource in resources}) == 100


def test_input_is_not_modified(patient):
    before = deepcopy(patient)
    patient_to_fhir(patient)
    assert patient == before


def test_output_is_json_serializable(patient):
    resource = patient_to_fhir(patient)
    assert json.loads(json.dumps(resource)) == resource


def test_internal_fields_are_not_emitted(patient):
    resource = patient_to_fhir(patient)
    assert "is_synthetic" not in resource
    assert "patient_id" not in resource
    assert "given_name" not in resource


def test_optional_demographics_are_not_invented(patient):
    resource = patient_to_fhir(patient)
    for field in ("gender", "telecom", "address", "active"):
        assert field not in resource


def test_invalid_source_is_rejected(patient):
    patient["is_synthetic"] = False
    with pytest.raises(ValidationError):
        patient_to_fhir(patient)


def test_non_dictionary_is_rejected():
    with pytest.raises(TypeError):
        patient_to_fhir([])
