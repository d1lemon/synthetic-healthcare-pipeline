"""Internal synthetic records; these are not FHIR resource models."""

from datetime import date
from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class SyntheticRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
    )

    is_synthetic: Literal[True]

    @field_validator("is_synthetic", mode="before")
    @classmethod
    def require_synthetic_label(cls, value):
        if value is not True:
            raise ValueError("is_synthetic must be the boolean True")
        return value


class PatientRecord(SyntheticRecord):
    patient_id: str = Field(
        strict=True,
        pattern=r"^syn-patient-[0-9]{4,}$",
    )
    given_name: str = Field(strict=True, min_length=1)
    family_name: str = Field(strict=True, min_length=1)
    birth_date: date

    @field_validator("given_name", "family_name")
    @classmethod
    def reject_blank_name(cls, value):
        if not value.strip():
            raise ValueError("name cannot contain only whitespace")
        return value


class ObservationRecord(SyntheticRecord):
    observation_id: str = Field(
        strict=True,
        pattern=r"^syn-observation-[0-9]{6,}$",
    )
    patient_id: str = Field(
        strict=True,
        pattern=r"^syn-patient-[0-9]{4,}$",
    )
    source_code: Literal[
        "heart_rate", "body_temperature", "body_weight"
    ]
    value: float = Field(strict=True)
    unit: str = Field(strict=True)
    observed_at: AwareDatetime
    status: Literal["final"]

    @model_validator(mode="after")
    def check_source_unit(self):
        expected_units = {
            "heart_rate": "beats/min",
            "body_temperature": "degC",
            "body_weight": "kg",
        }
        if self.unit != expected_units[self.source_code]:
            raise ValueError(
                "unit does not match the supported source measurement"
            )
        return self
