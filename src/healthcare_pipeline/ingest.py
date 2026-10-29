"""In-memory batch processing with explicit per-record outcomes."""

from pydantic import ValidationError

from healthcare_pipeline.map_fhir import patient_to_fhir
from healthcare_pipeline.map_observation import observation_to_fhir


def ingest_batch(patients: list, observations: list) -> dict:
    """Process patients first, then observations referencing them."""
    if not isinstance(patients, list) or not isinstance(observations, list):
        raise TypeError("patients and observations must be lists")

    accepted_patients = []
    accepted_observations = []
    audits = []
    outcomes = []
    patient_ids = set()
    observation_ids = set()

    def reject(resource_type, index, source, rule_id, message):
        source_key = (
            "patient_id"
            if resource_type == "Patient"
            else "observation_id"
        )
        record_id = (
            source.get(source_key) if isinstance(source, dict) else None
        )
        outcomes.append({
            "resource_type": resource_type,
            "input_index": index,
            "record_id": record_id,
            "status": "rejected",
            "issues": [{
                "rule_id": rule_id,
                "severity": "error",
                "message": message,
            }],
        })

    def accept(resource_type, index, resource):
        outcomes.append({
            "resource_type": resource_type,
            "input_index": index,
            "record_id": resource["id"],
            "status": "accepted",
            "issues": [],
        })

    for index, source in enumerate(patients):
        if not isinstance(source, dict):
            reject(
                "Patient", index, source, "SOURCE_TYPE",
                "Patient source must be a dictionary.",
            )
            continue

        try:
            resource = patient_to_fhir(source)
        except ValidationError:
            reject(
                "Patient", index, source, "PATIENT_VALIDATION",
                "Patient source failed internal model validation.",
            )
            continue

        if resource["id"] in patient_ids:
            reject(
                "Patient", index, source, "DUPLICATE_PATIENT_ID",
                "An accepted patient already uses this ID.",
            )
            continue

        patient_ids.add(resource["id"])
        accepted_patients.append(resource)
        accept("Patient", index, resource)

    for index, source in enumerate(observations):
        if not isinstance(source, dict):
            reject(
                "Observation", index, source, "SOURCE_TYPE",
                "Observation source must be a dictionary.",
            )
            continue

        try:
            resource, audit = observation_to_fhir(source)
        except (ValidationError, ValueError):
            reject(
                "Observation", index, source, "OBSERVATION_VALIDATION",
                "Observation failed source validation or normalization.",
            )
            continue

        if resource["id"] in observation_ids:
            reject(
                "Observation", index, source, "DUPLICATE_OBSERVATION_ID",
                "An accepted observation already uses this ID.",
            )
            continue

        if source["patient_id"] not in patient_ids:
            reject(
                "Observation", index, source, "UNKNOWN_PATIENT",
                "Referenced patient was not accepted in this batch.",
            )
            continue

        observation_ids.add(resource["id"])
        accepted_observations.append(resource)
        audits.append(audit)
        accept("Observation", index, resource)

    accepted_count = len(accepted_patients) + len(accepted_observations)
    input_count = len(patients) + len(observations)

    return {
        "summary": {
            "input_patients": len(patients),
            "input_observations": len(observations),
            "input_total": input_count,
            "accepted_patients": len(accepted_patients),
            "accepted_observations": len(accepted_observations),
            "accepted_total": accepted_count,
            "rejected_total": input_count - accepted_count,
            "independent_fhir_validation": "not_run",
        },
        "patients": accepted_patients,
        "observations": accepted_observations,
        "normalization_audits": audits,
        "outcomes": outcomes,
    }
