"""Map supported synthetic observations to FHIR R4 dictionaries."""

from healthcare_pipeline.normalize import normalize_observation


TERMINOLOGY = {
    "heart_rate": {
        "loinc": "8867-4",
        "display": "Heart rate",
        "unit": "beats/min",
        "ucum": "/min",
    },
    "body_temperature": {
        "loinc": "8310-5",
        "display": "Body temperature",
        "unit": "degC",
        "ucum": "Cel",
    },
    "body_weight": {
        "loinc": "29463-7",
        "display": "Body weight",
        "unit": "kg",
        "ucum": "kg",
    },
}


def observation_to_fhir(source: dict) -> tuple[dict, dict]:
    """Return a mapped resource and separate normalization audit."""
    observation, audit = normalize_observation(source)
    term = TERMINOLOGY[observation.source_code]

    resource = {
        "resourceType": "Observation",
        "id": observation.observation_id,
        "status": observation.status,
        "category": [{
            "coding": [{
                "system": (
                    "http://terminology.hl7.org/"
                    "CodeSystem/observation-category"
                ),
                "code": "vital-signs",
                "display": "Vital Signs",
            }],
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": term["loinc"],
                "display": term["display"],
            }],
        },
        "subject": {
            "reference": f"Patient/{observation.patient_id}",
        },
        "effectiveDateTime": observation.observed_at.isoformat(),
        "valueQuantity": {
            "value": observation.value,
            "unit": term["unit"],
            "system": "http://unitsofmeasure.org",
            "code": term["ucum"],
        },
    }

    return resource, audit
