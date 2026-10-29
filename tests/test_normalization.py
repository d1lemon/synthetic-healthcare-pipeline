from copy import deepcopy
from datetime import timedelta

import pytest
from pydantic import ValidationError

from healthcare_pipeline.generate import generate_patients
from healthcare_pipeline.generate_observations import (
    generate_observations,
)
from healthcare_pipeline.normalize import normalize_observation


@pytest.fixture
def observation():
    return generate_observations(
        generate_patients(count=1), observations_per_patient=1
    )[0]


def test_fahrenheit_to_celsius(observation):
    observation.update(
        source_code="body_temperature", value=98.6, unit="degF"
    )
    record, audit = normalize_observation(observation)
    assert record.value == pytest.approx(37.0)
    assert record.unit == "degC"
    assert audit["unit_converted"] is True
    assert audit["original"]["value"] == 98.6
    assert audit["original"]["unit"] == "degF"


def test_pounds_to_kilograms(observation):
    observation.update(
        source_code="body_weight", value=100.0, unit="lb"
    )
    record, audit = normalize_observation(observation)
    assert record.value == pytest.approx(45.359237)
    assert record.unit == "kg"
    assert audit["unit_converted"] is True


def test_timezone_conversion_preserves_instant(observation):
    observation["observed_at"] = "2026-01-01T12:00:00-05:00"
    record, audit = normalize_observation(observation)
    assert record.observed_at.isoformat() == (
        "2026-01-01T17:00:00+00:00"
    )
    assert record.observed_at.utcoffset() == timedelta(0)
    assert audit["timezone_offset_changed"] is True
    assert audit["original"]["observed_at"] == (
        "2026-01-01T12:00:00-05:00"
    )


def test_input_is_not_modified(observation):
    observation.update(
        source_code="body_weight", value=100.0, unit="lb"
    )
    before = deepcopy(observation)
    normalize_observation(observation)
    assert observation == before


def test_generated_data_requires_no_conversion():
    records = generate_observations(generate_patients(count=3))
    for source in records:
        record, audit = normalize_observation(source)
        assert record.value == source["value"]
        assert record.unit == source["unit"]
        assert audit["unit_converted"] is False
        assert audit["timezone_offset_changed"] is False


def test_normalized_output_is_idempotent(observation):
    observation.update(
        source_code="body_weight", value=100.0, unit="lb"
    )
    first, _ = normalize_observation(observation)
    second, audit = normalize_observation(
        first.model_dump(mode="json")
    )
    assert first == second
    assert audit["unit_converted"] is False


@pytest.mark.parametrize("value", [
    True, "64.0", None, float("nan"), float("inf")
])
def test_invalid_values_rejected(observation, value):
    observation["value"] = value
    with pytest.raises(ValueError):
        normalize_observation(observation)


def test_unsupported_unit_rejected(observation):
    observation["unit"] = "unknown"
    with pytest.raises(ValueError):
        normalize_observation(observation)


def test_naive_timestamp_rejected(observation):
    observation["observed_at"] = "2026-01-01T12:00:00"
    with pytest.raises(ValidationError):
        normalize_observation(observation)


def test_extra_field_is_not_silently_dropped(observation):
    observation["unexpected_field"] = "example"
    with pytest.raises(ValidationError):
        normalize_observation(observation)


def test_non_dictionary_rejected():
    with pytest.raises(TypeError):
        normalize_observation([])
