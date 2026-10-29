# FHIR Mapping Scope

Target: FHIR R4, version 4.0.1.

## Implementation decision

Use explicit Python dictionary mappings and existing Pydantic
source models. No FHIR model library is currently installed.

The metadata inspected for fhir.resources 6.4.0 does not establish
compatibility with the installed Pydantic 2 environment.
No compatibility failure is claimed because it was not tested.

## Patient mapping

| Source | FHIR destination |
| --- | --- |
| patient_id | id |
| family_name | name[0].family |
| given_name | name[0].given[0] |
| birth_date | birthDate |

resourceType is Patient.
The source patient_id is an application resource key, not an MRN.

Optional demographics are omitted when not supplied.
Internal is_synthetic is validated but not emitted as a custom
top-level FHIR field. Export artifacts must retain clear synthetic
labeling through their surrounding documentation or manifest.

## Validation limits

Tests verify our selected mappings and source validation.
They do not implement the complete FHIR schema, invariants,
terminology validation, or profile validation.
Independent R4 validation has not yet run.

## Specification

https://hl7.org/fhir/R4/patient.html

## Observation mapping

Implemented in src/healthcare_pipeline/map_observation.py.

The mapper normalizes supported units and timestamps, validates the
internal record, and returns a FHIR dictionary plus a separate audit.

| Source | FHIR destination |
| --- | --- |
| observation_id | id |
| status | status |
| source_code | code.coding via the terminology mapping |
| patient_id | subject.reference as Patient/{patient_id} |
| observed_at | effectiveDateTime, normalized to UTC |
| normalized value | valueQuantity.value |
| normalized unit | valueQuantity.unit |
| mapped UCUM code | valueQuantity.code |

resourceType is Observation.
category contains vital-signs.
code.coding.system is http://loinc.org.
valueQuantity.system is http://unitsofmeasure.org.

### Supported terminology

| Measurement | LOINC | Internal unit | UCUM code |
| --- | --- | --- | --- |
| Heart rate | 8867-4 | beats/min | /min |
| Body temperature | 8310-5 | degC | Cel |
| Body weight | 29463-7 | kg | kg |

### Normalization and audit

Supported alternate units are degF for body temperature and lb for
body weight. Timezone-aware timestamps are converted to UTC.
Naive timestamps and unsupported measurement/unit pairs are rejected.

Original value, unit, and timestamp are returned in a separate audit.
The audit is not inserted as a custom top-level FHIR field.
Neither the mapped resource nor the audit is persisted by the mapper.

### Relationship and conformance boundaries

A syntactically valid patient reference does not prove that the
referenced Patient exists. Dataset tests currently check references
for the generated demonstration dataset; the mapper itself does not.

No meta.profile conformance claim is emitted.
Independent FHIR R4 validation has not yet run.
Successful unit tests do not establish full FHIR conformance,
terminology-service validation, clinical accuracy, or production readiness.

### Observation specification

https://hl7.org/fhir/R4/observation.html
https://hl7.org/fhir/R4/observation-vitalsigns.html
