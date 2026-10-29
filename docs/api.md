# Read-only API

## Application factory

healthcare_pipeline.api.create_app(database_path)

Supply an explicit path to an existing, initialized SQLite database.
The application does not create or initialize the database.
API connections use SQLite read-only mode.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Application liveness only |
| GET | /patients | Paginated patients |
| GET | /patients/{patient_id} | Patient lookup |
| GET | /observations | Paginated observations |
| GET | /observations/{observation_id} | Observation lookup |
| GET | /reports/{run_id} | Stored run summary |

/observations accepts an optional patient_id query parameter.
List endpoints accept limit (1-100, default 20) and offset
(zero or greater, default 0).

## Responses

Single-resource lookups return stored resource JSON.
Missing resources and runs return 404.
Invalid pagination parameters return 422.

List responses contain items, total, limit, and offset.
An unknown patient filter returns an empty observation list.
Lists use resource-ID ordering for an unchanged dataset.

## Scope and limitations

This is an application API returning mapped FHIR R4 resources,
not a complete FHIR REST server.
List responses are not FHIR search Bundles.
Errors use FastAPI's application responses, not FHIR OperationOutcome.

/health does not verify database readiness.
No authentication, public hosting, or production security
configuration has been implemented.
No write endpoints are implemented.
Independent FHIR validation has not yet run.

Use only entirely synthetic data.
Do not expose this development application as a clinical service.

## Tests and dependencies

Endpoint tests use FastAPI TestClient without starting a public server.
FastAPI is an application dependency.
pytest and HTTPX are declared in the dev optional dependency group.
An ASGI server dependency and launch command are not yet configured.
