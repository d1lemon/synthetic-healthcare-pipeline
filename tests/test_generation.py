from datetime import date
import random

import pytest

from healthcare_pipeline.generate import generate_patients


def test_requested_patient_count():
    assert len(generate_patients(count=100)) == 100


def test_same_seed_produces_identical_records():
    assert generate_patients(seed=42) == generate_patients(seed=42)


def test_different_seed_changes_birth_dates():
    assert generate_patients(seed=42) != generate_patients(seed=43)


def test_patient_ids_are_unique():
    patients = generate_patients(count=100)
    identifiers = [patient["patient_id"] for patient in patients]
    assert len(identifiers) == len(set(identifiers))


def test_records_are_explicitly_synthetic():
    for patient in generate_patients(count=10):
        assert patient["is_synthetic"] is True
        assert patient["patient_id"].startswith("syn-patient-")
        assert patient["given_name"].startswith("SyntheticGiven")
        assert patient["family_name"].startswith("SyntheticFamily")


def test_birth_dates_are_parseable_and_in_configured_range():
    for patient in generate_patients():
        birth_date = date.fromisoformat(patient["birth_date"])
        assert date(1940, 1, 1) <= birth_date <= date(2020, 12, 31)


def test_zero_count_returns_empty_list():
    assert generate_patients(count=0) == []


def test_negative_count_is_rejected():
    with pytest.raises(ValueError):
        generate_patients(count=-1)


@pytest.mark.parametrize("count", [True, 1.5, "10", None])
def test_non_integer_count_is_rejected(count):
    with pytest.raises(TypeError):
        generate_patients(count=count)


@pytest.mark.parametrize("seed", [True, 1.5, "42", None])
def test_non_integer_seed_is_rejected(seed):
    with pytest.raises(TypeError):
        generate_patients(seed=seed)


def test_generator_does_not_change_global_random_state():
    state_before = random.getstate()
    generate_patients()
    assert random.getstate() == state_before
