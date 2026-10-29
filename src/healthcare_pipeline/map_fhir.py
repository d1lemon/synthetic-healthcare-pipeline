"""Explicit FHIR R4 mappings; not a full FHIR validation library."""

from healthcare_pipeline.models import PatientRecord


FHIR_VERSION = "4.0.1"


def patient_to_fhir(source: dict) -> dict:
    """Map a validated synthetic source record to a Patient resource."""
    if not isinstance(source, dict):
        raise TypeError("source must be a dictionary")

    patient = PatientRecord.model_validate(source)

    return {
        "resourceType": "Patient",
        "id": patient.patient_id,
        "name": [{
            "family": patient.family_name,
            "given": [patient.given_name],
        }],
        "birthDate": patient.birth_date.isoformat(),
    }
