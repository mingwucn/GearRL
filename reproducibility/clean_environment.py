"""Independent locked-prefix reproduction and attestation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import time
from typing import Sequence


@dataclass(frozen=True)
class CleanEnvironmentConfig:
    source_commit: str
    conda_executable: Path
    prefix: Path
    lockfile: Path
    pip_requirements: Path


@dataclass(frozen=True)
class CommandEvidence:
    command_id: str
    argv: tuple[str, ...]
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    elapsed_seconds: float


class CommandRunner(ABC):
    @abstractmethod
    def run(self, command_id: str, argv: Sequence[str], cwd: Path | None = None, environment: dict[str, str] | None = None) -> tuple[CommandEvidence, str, str]:
        raise NotImplementedError


class SubprocessCommandRunner(CommandRunner):
    def run(self, command_id: str, argv: Sequence[str], cwd: Path | None = None, environment: dict[str, str] | None = None) -> tuple[CommandEvidence, str, str]:
        started = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=environment, text=True, capture_output=True, check=False)
        evidence = CommandEvidence(
            command_id=command_id,
            argv=tuple(map(str, argv)),
            exit_code=result.returncode,
            stdout_sha256=sha256(result.stdout.encode()).hexdigest(),
            stderr_sha256=sha256(result.stderr.encode()).hexdigest(),
            elapsed_seconds=round(time.monotonic() - started, 6),
        )
        if result.returncode:
            raise RuntimeError(f"Clean reproduction command failed ({command_id}):\n{result.stdout}\n{result.stderr}")
        return evidence, result.stdout, result.stderr


class GitCommitExporter:
    """Export only committed source, excluding the caller's working tree."""

    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def export(self, commit: str, repository: Path, destination: Path) -> CommandEvidence:
        archive = destination.parent / "source.tar"
        evidence, _, _ = self._runner.run("git-archive", ["git", "archive", "--format=tar", "--output", str(archive), commit], repository)
        destination.mkdir(parents=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(destination, filter="data")
        archive.unlink()
        return evidence


class SourceTreeHasher:
    def digest(self, root: Path) -> str:
        digest = sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(path.read_bytes())
        return digest.hexdigest()


class CleanEnvironmentAttestor:
    """Create a locked prefix and execute the complete committed verification set."""

    VERIFICATIONS = (
        ("regression-suite", ("-m", "pytest", "-q")),
        ("publication-artifacts", ("run_publication_artifacts.py", "--verify", "paper/generated-v1")),
        ("literature-artifact", ("run_literature_matrix.py", "--verify", "paper/literature-v1")),
        ("manuscript-artifact", ("run_manuscript.py", "--verify", "paper/manuscript-v1")),
        ("readiness-artifact", ("run_submission_readiness.py", "--verify", "paper/submission-readiness-v1")),
        ("aei-package", ("run_aei_submission.py", "--verify", "paper/aei-submission-v1")),
    )

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or SubprocessCommandRunner()

    def run(self, config: CleanEnvironmentConfig, repository: Path) -> dict:
        if config.prefix.exists():
            raise FileExistsError(f"Clean prefix already exists: {config.prefix}")
        records: list[CommandEvidence] = []
        record, _, _ = self._runner.run("conda-create", [str(config.conda_executable), "create", "--yes", "--prefix", str(config.prefix), "--file", str(config.lockfile)], repository)
        records.append(record)
        python = config.prefix / "bin" / "python"
        record, _, _ = self._runner.run("pip-install", [str(python), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "--requirement", str(config.pip_requirements)], repository)
        records.append(record)
        with TemporaryDirectory(prefix="gearrl-committed-source-") as temporary:
            source = Path(temporary) / "source"
            records.append(GitCommitExporter(self._runner).export(config.source_commit, repository, source))
            source_sha256 = SourceTreeHasher().digest(source)
            for command_id, arguments in self.VERIFICATIONS:
                record, _, _ = self._runner.run(command_id, [str(python), *arguments], source)
                records.append(record)
        explicit, explicit_text, _ = self._runner.run("conda-explicit", [str(config.conda_executable), "list", "--explicit", "--prefix", str(config.prefix)], repository)
        records.append(explicit)
        freeze, freeze_text, _ = self._runner.run("pip-freeze", [str(python), "-m", "pip", "freeze", "--all"], repository)
        records.append(freeze)
        return {
            "schema_version": "clean-environment-attestation-v1",
            "source_commit": config.source_commit,
            "source_tree_sha256": source_sha256,
            "lockfile": str(config.lockfile),
            "lockfile_sha256": sha256(config.lockfile.read_bytes()).hexdigest(),
            "pip_requirements": str(config.pip_requirements),
            "pip_requirements_sha256": sha256(config.pip_requirements.read_bytes()).hexdigest(),
            "conda_explicit_sha256": sha256(explicit_text.encode()).hexdigest(),
            "pip_freeze_sha256": sha256(freeze_text.encode()).hexdigest(),
            "verification_count": len(self.VERIFICATIONS),
            "all_commands_passed": True,
            "commands": [record.__dict__ for record in records],
        }


class CleanEnvironmentEvidenceStore:
    """Persist an immutable attestation and its raw environment inventories."""

    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, report: dict, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Attestation destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        report_bytes = self._encode(report)
        (destination / "report.json").write_bytes(report_bytes)
        manifest = {
            "schema_version": "clean-environment-attestation-artifact-v1",
            "report_sha256": sha256(report_bytes).hexdigest(),
        }
        path = destination / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        report = (destination / "report.json").read_bytes()
        if sha256(report).hexdigest() != manifest["report_sha256"]:
            raise ValueError("Clean-environment report hash mismatch")
        payload = json.loads(report)
        if not payload["all_commands_passed"] or payload["verification_count"] != len(CleanEnvironmentAttestor.VERIFICATIONS):
            raise ValueError("Clean-environment attestation is incomplete")
        return payload
