"""Read-only queries for stored resources and run summaries."""

import json


def validate_pagination(limit: int, offset: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise TypeError("offset must be an integer")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if offset < 0:
        raise ValueError("offset cannot be negative")


def get_patient(connection, patient_id: str):
    row = connection.execute(
        "SELECT resource_json FROM patients WHERE patient_id = ?",
        (patient_id,),
    ).fetchone()
    return None if row is None else json.loads(row["resource_json"])


def get_observation(connection, observation_id: str):
    row = connection.execute(
        "SELECT resource_json FROM observations WHERE observation_id = ?",
        (observation_id,),
    ).fetchone()
    return None if row is None else json.loads(row["resource_json"])


def list_patients(connection, limit: int = 20, offset: int = 0) -> dict:
    validate_pagination(limit, offset)
    total = connection.execute(
        "SELECT COUNT(*) FROM patients"
    ).fetchone()[0]
    rows = connection.execute(
        """
        SELECT resource_json FROM patients
        ORDER BY patient_id LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    return {
        "items": [json.loads(row["resource_json"]) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_observations(
    connection,
    patient_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    validate_pagination(limit, offset)

    if patient_id is None:
        condition = ""
        parameters = ()
    else:
        condition = " WHERE patient_id = ?"
        parameters = (patient_id,)

    total = connection.execute(
        "SELECT COUNT(*) FROM observations" + condition,
        parameters,
    ).fetchone()[0]
    rows = connection.execute(
        "SELECT resource_json FROM observations"
        + condition
        + " ORDER BY observation_id LIMIT ? OFFSET ?",
        (*parameters, limit, offset),
    ).fetchall()
    return {
        "items": [json.loads(row["resource_json"]) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_run_summary(connection, run_id: str):
    row = connection.execute(
        """
        SELECT run_id, started_at, summary_json
        FROM ingestion_runs WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "run_id": row["run_id"],
        "started_at": row["started_at"],
        "summary": json.loads(row["summary_json"]),
    }
