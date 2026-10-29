"""Read-only educational API; not a complete FHIR server."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query

from healthcare_pipeline.repository import (
    get_patient,
    get_observation,
    get_run_summary,
    list_patients,
    list_observations,
)


def create_app(database_path) -> FastAPI:
    path = Path(database_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Select an existing SQLite database")

    app = FastAPI(
        title="Synthetic Healthcare Interoperability Demo",
        version="0.1.0",
        description=(
            "Entirely synthetic data. Read-only application endpoints "
            "returning mapped FHIR R4 resources. Not a complete FHIR "
            "server, clinical service, or HIPAA compliance claim. "
            "Independent FHIR validation has not yet run."
        ),
    )

    @contextmanager
    def read_connection():
        connection = sqlite3.connect(
            path.as_uri() + "?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only = ON")
            yield connection
        finally:
            connection.close()

    def require_found(value, message):
        if value is None:
            raise HTTPException(status_code=404, detail=message)
        return value

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "dataset": "synthetic",
            "fhir_target": "4.0.1",
        }

    @app.get("/patients")
    def patients(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        with read_connection() as connection:
            return list_patients(connection, limit, offset)

    @app.get("/patients/{patient_id}")
    def patient(patient_id: str):
        with read_connection() as connection:
            return require_found(
                get_patient(connection, patient_id),
                "Patient not found",
            )

    @app.get("/observations")
    def observations(
        patient_id: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ):
        with read_connection() as connection:
            return list_observations(
                connection,
                patient_id=patient_id,
                limit=limit,
                offset=offset,
            )

    @app.get("/observations/{observation_id}")
    def observation(observation_id: str):
        with read_connection() as connection:
            return require_found(
                get_observation(connection, observation_id),
                "Observation not found",
            )

    @app.get("/reports/{run_id}")
    def report(run_id: str):
        with read_connection() as connection:
            return require_found(
                get_run_summary(connection, run_id),
                "Run not found",
            )

    return app
