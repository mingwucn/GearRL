from pathlib import Path
from hashlib import sha256
import subprocess

import pytest

from reproducibility.clean_environment import CleanEnvironmentAttestationPolicy, CleanEnvironmentAttestor, CleanEnvironmentEvidenceStore, CleanEnvironmentReportValidator, CommittedSourceTreeHasher, SourceTreeHasher


def test_source_tree_hash_is_path_and_content_sensitive(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "value.txt").write_text("one")
    hasher = SourceTreeHasher()
    original = hasher.digest(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("changing metadata")
    assert hasher.digest(tmp_path) == original
    (tmp_path / "a" / "value.txt").write_text("two")
    assert hasher.digest(tmp_path) != original


def test_committed_and_checked_out_tree_hashes_share_canonical_order(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.org"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=repository, check=True)
    for relative in (Path("data/case/index.json"), Path("data/case-r2/index.json")):
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative.as_posix())
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-qm", "source"), cwd=repository, check=True)
    commit = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repository, text=True, capture_output=True, check=True).stdout.strip()

    assert CommittedSourceTreeHasher().digest(repository, commit) == SourceTreeHasher().digest(repository)


def test_evidence_store_requires_complete_success(tmp_path: Path) -> None:
    store = CleanEnvironmentEvidenceStore()
    root = tmp_path / "evidence"
    digest = "0" * 64
    report = {
        "schema_version": "clean-environment-attestation-v1",
        "all_commands_passed": True,
        "verification_count": len(CleanEnvironmentAttestor.VERIFICATIONS),
        "source_commit": "abc",
        "source_tree_sha256": digest,
        "lockfile_sha256": digest,
        "pip_requirements_sha256": digest,
        "conda_explicit_sha256": digest,
        "pip_freeze_sha256": digest,
        "commands": [
            {"command_id": command_id, "argv": [command_id], "exit_code": 0, "stdout_sha256": digest, "stderr_sha256": digest}
            for command_id in CleanEnvironmentReportValidator.expected_command_ids()
        ],
    }
    store.write(report, root)
    assert store.verify(root)["source_commit"] == "abc"
    (root / "report.json").write_text("{}\n")
    with pytest.raises(ValueError, match="report hash mismatch"):
        store.verify(root)


def test_report_validator_rejects_missing_command_evidence() -> None:
    payload = {"schema_version": "clean-environment-attestation-v1", "all_commands_passed": True, "verification_count": len(CleanEnvironmentAttestor.VERIFICATIONS), "commands": []}
    with pytest.raises(ValueError, match="command ledger mismatch"):
        CleanEnvironmentReportValidator().validate(payload)


def test_attestation_policy_allows_only_declared_artifact_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.org"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=repository, check=True)
    (repository / "science.py").write_text("VALUE = 1\n")
    (repository / "environment-ai.lock").write_text("locked\n")
    (repository / "requirements-ai-pip.txt").write_text("package==1 --hash=sha256:abc\n")
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-qm", "source"), cwd=repository, check=True)
    commit = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repository, text=True, capture_output=True, check=True).stdout.strip()
    payload = {
        "source_commit": commit,
        "source_tree_sha256": CommittedSourceTreeHasher().digest(repository, commit),
        "lockfile_sha256": sha256((repository / "environment-ai.lock").read_bytes()).hexdigest(),
        "pip_requirements_sha256": sha256((repository / "requirements-ai-pip.txt").read_bytes()).hexdigest(),
    }
    artifact = repository / "evidence" / "report.json"
    artifact.parent.mkdir()
    artifact.write_text("{}\n")
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-qm", "attestation"), cwd=repository, check=True)
    policy = CleanEnvironmentAttestationPolicy(
        repository,
        repository / "environment-ai.lock",
        repository / "requirements-ai-pip.txt",
        (Path("evidence/report.json"),),
    )
    policy.validate(payload)
    (repository / "science.py").write_text("VALUE = 2\n")
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-qm", "science drift"), cwd=repository, check=True)
    with pytest.raises(ValueError, match="stale for committed path: science.py"):
        policy.validate(payload)
