"""Generate fictional measurements for synthetic patients."""

from datetime import datetime, timedelta, timezone
import random


MEASUREMENT_TYPES = (
    ("heart_rate", "beats/min", 60.0, 100.0, 0),
    ("body_temperature", "degC", 36.0, 38.0, 1),
    ("body_weight", "kg", 50.0, 100.0, 1),
)


def generate_observations(
    patients: list[dict],
    observations_per_patient: int = 10,
    seed: int = 42,
) -> list[dict]:
    """Generate reproducible examples, not realistic clinical histories."""
    if (
        isinstance(observations_per_patient, bool)
        or not isinstance(observations_per_patient, int)
    ):
        raise TypeError("observations_per_patient must be an integer")
    if observations_per_patient < 0:
        raise ValueError("observations_per_patient cannot be negative")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not isinstance(patients, list):
        raise TypeError("patients must be a list")

    identifiers = []
    for patient in patients:
        if not isinstance(patient, dict):
            raise TypeError("each patient must be a dictionary")
        identifier = patient.get("patient_id")
        if (
            not isinstance(identifier, str)
            or not identifier.startswith("syn-patient-")
            or not identifier.removeprefix("syn-patient-").strip()
        ):
            raise ValueError("each patient needs a synthetic patient_id")
        if patient.get("is_synthetic") is not True:
            raise ValueError("each patient must be labeled synthetic")
        identifiers.append(identifier)

    if len(set(identifiers)) != len(identifiers):
        raise ValueError("patient IDs must be unique")

    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observations = []

    for patient_id in identifiers:
        for index in range(observations_per_patient):
            code, unit, lower, upper, precision = (
                MEASUREMENT_TYPES[index % len(MEASUREMENT_TYPES)]
            )
            observed_at = start + timedelta(
                days=index,
                minutes=rng.randrange(1440),
            )
            observations.append({
                "observation_id": (
                    f"syn-observation-{len(observations) + 1:06d}"
                ),
                "patient_id": patient_id,
                "source_code": code,
                "value": round(rng.uniform(lower, upper), precision),
                "unit": unit,
                "observed_at": observed_at.isoformat(),
                "status": "final",
                "is_synthetic": True,
            })

    return observations
