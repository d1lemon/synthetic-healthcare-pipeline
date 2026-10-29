"""Write reports for synthetic in-memory ingestion results."""

from collections import Counter
import csv
import json
from pathlib import Path
import re


def write_reports(result: dict, output_dir, run_id: str) -> dict:
    """Write JSON, issue CSV, and Markdown without overwriting files."""
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id
    ):
        raise ValueError("run_id must be 1-64 safe filename characters")

    summary = result["summary"]
    outcomes = result["outcomes"]

    if summary["input_total"] != len(outcomes):
        raise ValueError("Input count does not match outcome count")

    counts = Counter(item["status"] for item in outcomes)
    if set(counts) - {"accepted", "rejected"}:
        raise ValueError("Unsupported outcome status")
    if (
        counts["accepted"] != summary["accepted_total"]
        or counts["rejected"] != summary["rejected_total"]
    ):
        raise ValueError("Summary and outcome totals do not reconcile")

    issues = []
    for outcome in outcomes:
        for issue in outcome["issues"]:
            issues.append({
                "resource_type": outcome["resource_type"],
                "input_index": outcome["input_index"],
                "record_id": outcome["record_id"],
                "rule_id": issue["rule_id"],
                "severity": issue["severity"],
                "message": issue["message"],
            })

    issue_counts = dict(sorted(Counter(
        issue["rule_id"] for issue in issues
    ).items()))

    payload = {
        "run_id": run_id,
        "dataset_type": "entirely_synthetic",
        "summary": summary,
        "issue_counts_by_rule": issue_counts,
        "outcomes": outcomes,
    }
    json_text = json.dumps(payload, indent=2, allow_nan=False) + "\n"

    output_dir = Path(output_dir)
    paths = {
        "json": output_dir / f"{run_id}.json",
        "csv": output_dir / f"{run_id}_issues.csv",
        "markdown": output_dir / f"{run_id}.md",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Report files already exist for this run_id")

    markdown = [
        "# Synthetic Pipeline Validation Report",
        "",
        f"Run ID: {run_id}",
        "",
        "Dataset: entirely synthetic.",
        "",
        f"- Input patients: {summary['input_patients']}",
        f"- Input observations: {summary['input_observations']}",
        f"- Input total: {summary['input_total']}",
        f"- Accepted total: {summary['accepted_total']}",
        f"- Rejected total: {summary['rejected_total']}",
        f"- Validation issue count: {len(issues)}",
        "",
        "## Issues by rule",
        "",
    ]
    markdown.extend(
        f"- {rule}: {count}" for rule, count in issue_counts.items()
    )
    if not issue_counts:
        markdown.append("- None")

    markdown.extend([
        "",
        "## Validation boundary",
        "",
        "These results reflect implemented application checks.",
        "Independent FHIR validation: "
        + summary["independent_fhir_validation"],
        "This report does not establish full FHIR conformance "
        "or clinical accuracy.",
        "",
    ])

    output_dir.mkdir(parents=True, exist_ok=True)

    with paths["json"].open("x", encoding="utf-8") as handle:
        handle.write(json_text)

    fields = [
        "resource_type", "input_index", "record_id",
        "rule_id", "severity", "message",
    ]
    with paths["csv"].open(
        "x", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(issues)

    with paths["markdown"].open("x", encoding="utf-8") as handle:
        handle.write("\n".join(markdown))

    return paths
