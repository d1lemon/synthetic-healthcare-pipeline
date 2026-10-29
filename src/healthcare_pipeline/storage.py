"""Persist application ingestion results in a single transaction."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3


class ResourceConflictError(ValueError):
    """An existing resource ID has different content."""


def canonical_json(value) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def store_batch(connection, result: dict, run_id: str) -> dict:
    """Persist a trusted ingest_batch result; return storage outcomes."""
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a nonempty string")
    if connection.in_transaction:
        raise RuntimeError("Storage requires no active transaction")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("Foreign-key enforcement must be enabled")

    stored = deepcopy(result)
    outcomes = stored["outcomes"]
    if len(outcomes) != stored["summary"]["input_total"]:
        raise ValueError("Outcome count does not match input count")

    accepted_outcomes = {
        (item["resource_type"], item["record_id"]): item
        for item in outcomes if item["status"] == "accepted"
    }

    with connection:
        connection.execute(
            """
            INSERT INTO ingestion_runs
            (run_id, started_at, summary_json)
            VALUES (?, ?, ?)
            """,
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                "{}",
            ),
        )

        for resource_type, resources, table, id_column in (
            ("Patient", stored["patients"], "patients", "patient_id"),
            (
                "Observation", stored["observations"],
                "observations", "observation_id",
            ),
        ):
            for resource in resources:
                identifier = resource["id"]
                payload = canonical_json(resource)
                existing = connection.execute(
                    f"SELECT resource_json FROM {table} "
                    f"WHERE {id_column} = ?",
                    (identifier,),
                ).fetchone()

                if existing is not None:
                    if existing["resource_json"] != payload:
                        raise ResourceConflictError(
                            f"Conflicting {resource_type} ID: {identifier}"
                        )
                    accepted_outcomes[
                        (resource_type, identifier)
                    ]["status"] = "skipped"
                    continue

                if resource_type == "Patient":
                    connection.execute(
                        "INSERT INTO patients VALUES (?, ?)",
                        (identifier, payload),
                    )
                else:
                    reference = resource["subject"]["reference"]
                    if not reference.startswith("Patient/"):
                        raise ValueError("Unsupported patient reference")
                    connection.execute(
                        """
                        INSERT INTO observations
                        (observation_id, patient_id, code,
                         observed_at, resource_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            identifier,
                            reference.removeprefix("Patient/"),
                            resource["code"]["coding"][0]["code"],
                            resource["effectiveDateTime"],
                            payload,
                        ),
                    )

        summary = stored["summary"]
        summary["accepted_patients"] = sum(
            item["status"] == "accepted"
            and item["resource_type"] == "Patient"
            for item in outcomes
        )
        summary["accepted_observations"] = sum(
            item["status"] == "accepted"
            and item["resource_type"] == "Observation"
            for item in outcomes
        )
        summary["accepted_total"] = sum(
            item["status"] == "accepted" for item in outcomes
        )
        summary["skipped_total"] = sum(
            item["status"] == "skipped" for item in outcomes
        )
        summary["rejected_total"] = sum(
            item["status"] == "rejected" for item in outcomes
        )

        for item in outcomes:
            connection.execute(
                """
                INSERT INTO record_outcomes
                (run_id, resource_type, input_index,
                 record_id, status, issues_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, item["resource_type"], item["input_index"],
                    item["record_id"], item["status"],
                    canonical_json(item["issues"]),
                ),
            )

        for audit in stored["normalization_audits"]:
            connection.execute(
                "INSERT INTO normalization_audits VALUES (?, ?, ?)",
                (
                    run_id, audit["observation_id"],
                    canonical_json(audit),
                ),
            )

        connection.execute(
            "UPDATE ingestion_runs SET summary_json = ? WHERE run_id = ?",
            (canonical_json(summary), run_id),
        )

    return {
        "run_id": run_id,
        "summary": stored["summary"],
        "outcomes": outcomes,
    }
