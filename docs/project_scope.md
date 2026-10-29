# MVP Scope

## Target

FHIR R4, version 4.0.1.

## Initial resources

- Patient
- Observation

## Initial measurement types

- Heart rate
- Body temperature
- Body weight

## Planned components

- Seeded synthetic data generator
- Internal data models
- Normalization and terminology mapping
- FHIR resource mapping
- Layered validation
- SQLite persistence
- Read-only FastAPI endpoints
- Validation reports and automated tests

## Deferred

- HL7 v2 and C-CDA adapters
- Public deployment
- Interactive website showcase
- Production authentication and authorization

## Validation boundary

Python model validation must not be described as full FHIR
conformance validation. Document the rules and profiles actually tested.
