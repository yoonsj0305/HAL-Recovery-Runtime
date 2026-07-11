import json
from pathlib import Path
from zipfile import ZipFile

from scripts.package_release import build_release_zip


def test_public_release_files_and_required_statements_exist():
    required = (
        "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "CITATION.cff",
        "PUBLIC_POC_MANIFEST.json", "docs/CLI_REFERENCE.md", "docs/PUBLIC_POC_WORKFLOW.md",
        "docs/ARTIFACT_CONTRACT.md", "docs/LIMITATIONS.md", "docs/THREAT_MODEL.md",
    )
    assert not [name for name in required if not Path(name).is_file()]
    manifest = json.loads(Path("PUBLIC_POC_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.0.0"
    assert manifest["simulation_only"] is True
    assert manifest["hardware_control_enabled"] is False
    limitations = Path("docs/LIMITATIONS.md").read_text(encoding="utf-8")
    assert "Artifact integrity and review provenance do not prove physical chip recovery." in limitations
    artifact_contract = Path("docs/ARTIFACT_CONTRACT.md").read_text(encoding="utf-8")
    assert artifact_contract.count("No artifact authorizes hardware control.") >= 17


def test_public_release_zip_contains_contract_docs_and_example(tmp_path):
    archive_path = build_release_zip(tmp_path / "hal-recovery-runtime-v1.0.0.zip")
    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    required = {
        "hal-recovery-runtime/PUBLIC_POC_MANIFEST.json",
        "hal-recovery-runtime/SECURITY.md",
        "hal-recovery-runtime/docs/PUBLIC_POC_WORKFLOW.md",
        "hal-recovery-runtime/docs/ARTIFACT_CONTRACT.md",
        "hal-recovery-runtime/examples/public_poc/input/test_log.csv",
        "hal-recovery-runtime/examples/public_poc/review_decision_approved.json",
        "hal-recovery-runtime/src/hal_runtime/release_contract.py",
        "hal-recovery-runtime/src/hal_runtime/public_poc_validator.py",
    }
    assert required <= names
