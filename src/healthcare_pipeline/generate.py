"""Generate fictional patient records without external source data."""

from datetime import date, timedelta
import random


def generate_patients(
    count: int = 100,
    seed: int = 42,
) -> list[dict[str, str | bool]]:
    """Return reproducible, explicitly synthetic patient records."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be an integer")
    if count < 0:
        raise ValueError("count must be zero or greater")

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    first_birth_date = date(1940, 1, 1)
    last_birth_date = date(2020, 12, 31)
    date_span = (last_birth_date - first_birth_date).days

    patients = []
    for index in range(1, count + 1):
        birth_date = first_birth_date + timedelta(
            days=rng.randint(0, date_span)
        )

        patients.append({
            "patient_id": f"syn-patient-{index:04d}",
            "given_name": f"SyntheticGiven{index:04d}",
            "family_name": f"SyntheticFamily{index:04d}",
            "birth_date": birth_date.isoformat(),
            "is_synthetic": True,
        })

    return patients
