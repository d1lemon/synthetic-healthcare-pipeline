# SQLite Storage

## Implementation

- database.py: connections and schema initialization.
- storage.py: transactional persistence of ingest_batch results.
- reports.py: reports supporting accepted, skipped, and rejected outcomes.

Uses Python's built-in sqlite3 module.
Foreign-key enforcement is enabled and checked on each connection
created by connect_database.

## Tables

- patients: resource ID and canonical FHIR JSON.
- observations: resource ID, patient reference, code, timestamp, and JSON.
- ingestion_runs: run ID, storage start timestamp, and summary.
- record_outcomes: per-input status and issues associated with a run.
- normalization_audits: observation normalization audit per run.

## Transaction and duplicate rules

- New resource ID: insert.
- Existing ID with identical canonical JSON: skip.
- Existing ID with different content: abort and roll back the entire run.
- Reused run ID: reject without changing existing stored results.
- No resource overwrite or update behavior is implemented.
- Failed transactions are not retained as completed ingestion runs.

Canonical JSON comparison ignores dictionary key ordering, but does not
establish clinical or semantic equivalence between different payloads.

## Outcome reconciliation

input_total = accepted_total + skipped_total + rejected_total

For stored results, accepted means newly inserted.
Skipped means an identical resource was already stored.

Audits are retained for each successfully stored run, including skipped
observations. Repeated runs therefore add audits and outcomes, but do
not duplicate identical patient or observation resources.

## Current boundaries

store_batch expects a trusted result produced by ingest_batch.
It is not a public upload interface or a full FHIR validator.

ingest_batch currently resolves observation references against accepted
patients in the supplied batch, not against patients already in SQLite.
Include the relevant patients when submitting a batch.

Raw rejected source payloads are not persisted.
Validation issues are stored within record_outcomes.issues_json.
Schema migrations and resource update/delete workflows are not implemented.

Independent FHIR validation has not yet run.

## Demonstration

A two-run demonstration verified:
- 100 patients and 1,000 observations stored.
- First run inserted 1,100 resources.
- Second run skipped 1,100 identical resources.
- 2 ingestion runs, 2,200 outcomes, and 2,000 normalization audits.
- Successful reconnection and matching stored summaries.
- Passing foreign-key consistency and SQLite integrity checks.

Generated databases and reports remain ignored and untracked.
