"""Normalize supported source observations and preserve an audit."""

from copy import deepcopy
from datetime import timezone
import math

from healthcare_pipeline.models import ObservationRecord


def normalize_observation(source: dict) -> tuple[ObservationRecord, dict]:
    """Return a validated record and a separate normalization audit."""
    if not isinstance(source, dict):
        raise TypeError("source must be a dictionary")

    candidate = deepcopy(source)
    original = {
        key: deepcopy(source.get(key))
        for key in ("value", "unit", "observed_at")
    }

    code = candidate.get("source_code")
    unit = candidate.get("unit")
    value = candidate.get("value")

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a finite numeric value")

    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError("value must be a finite numeric value")

    converted = False

    if code == "heart_rate" and unit == "beats/min":
        pass
    elif code == "body_temperature" and unit == "degC":
        pass
    elif code == "body_temperature" and unit == "degF":
        candidate["value"] = (value - 32) / 1.8
        candidate["unit"] = "degC"
        converted = True
    elif code == "body_weight" and unit == "kg":
        pass
    elif code == "body_weight" and unit == "lb":
        candidate["value"] = value * 0.45359237
        candidate["unit"] = "kg"
        converted = True
    else:
        raise ValueError("unsupported measurement and unit combination")

    validated = ObservationRecord.model_validate(candidate)
    normalized = validated.model_copy(update={
        "observed_at": validated.observed_at.astimezone(timezone.utc)
    })

    audit = {
        "observation_id": normalized.observation_id,
        "original": original,
        "normalized": {
            "value": normalized.value,
            "unit": normalized.unit,
            "observed_at": normalized.observed_at.isoformat(),
        },
        "unit_converted": converted,
        "timezone_offset_changed": (
            validated.observed_at.utcoffset()
            != normalized.observed_at.utcoffset()
        ),
    }

    return normalized, audit
