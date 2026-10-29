from pathlib import Path

import healthcare_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_package_version():
    assert healthcare_pipeline.__version__ == "0.1.0"


def test_readme_exists():
    assert (PROJECT_ROOT / "README.md").is_file()


def test_synthetic_data_policy_exists():
    policy = PROJECT_ROOT / "docs" / "synthetic_data_policy.md"
    assert policy.is_file()
    assert "Do not accept real patient uploads." in policy.read_text(
        encoding="utf-8"
    )


def test_project_scope_declares_fhir_target():
    scope = PROJECT_ROOT / "docs" / "project_scope.md"
    assert "FHIR R4, version 4.0.1." in scope.read_text(
        encoding="utf-8"
    )
