"""Independent locked-prefix reproduction and attestation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
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


class GitCommitCheckout:
    """Checkout a detached local clone, excluding the caller's working tree."""

    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def checkout(self, commit: str, repository: Path, destination: Path) -> tuple[CommandEvidence, CommandEvidence]:
        clone, _, _ = self._runner.run("git-clone", ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(repository), str(destination)], repository)
        checkout, _, _ = self._runner.run("git-checkout", ["git", "checkout", "--quiet", "--detach", commit], destination)
        return clone, checkout


class SourceTreeHasher:
    def digest(self, root: Path) -> str:
        digest = sha256()
        for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.relative_to(root).parts):
            digest.update(path.relative_to(root).as_posix().encode() + b"\0")
            digest.update(path.read_bytes())
        return digest.hexdigest()


class CommittedSourceTreeHasher:
    """Hash a committed tree without trusting the caller's working tree."""

    def digest(self, repository: Path, commit: str) -> str:
        paths = subprocess.run(
            ("git", "ls-tree", "-r", "--name-only", commit),
            cwd=repository,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        digest = sha256()
        for path in sorted(paths):
            content = subprocess.run(
                ("git", "show", f"{commit}:{path}"),
                cwd=repository,
                capture_output=True,
                check=True,
            ).stdout
            digest.update(path.encode() + b"\0")
            digest.update(content)
        return digest.hexdigest()


class CleanEnvironmentAttestor:
    """Create a locked prefix and execute the complete committed verification set."""

    VERIFICATIONS = (
        ("regression-suite", ("-m", "pytest", "-q")),
        ("publication-artifacts", ("run_publication_artifacts.py", "--verify", "paper/generated-v2")),
        ("literature-artifact", ("run_literature_matrix.py", "--verify", "paper/literature-v1")),
        ("manuscript-artifact", ("run_manuscript.py", "--verify", "paper/manuscript-v2")),
        ("aei-package", ("run_aei_submission.py", "--verify", "paper/aei-submission-v2")),
        ("assembly-robustness-pilot", ("run_assembly_robustness.py", "--verify", "data/results/assembly-robustness-v1")),
        ("assembly-robustness-confirmatory", ("run_confirmatory_assembly.py", "--verify", "data/results/assembly-robustness-confirmatory-v3")),
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
            records.extend(GitCommitCheckout(self._runner).checkout(config.source_commit, repository, source))
            source_sha256 = SourceTreeHasher().digest(source)
            clean_environment = os.environ.copy()
            clean_environment["PATH"] = str(config.prefix / "bin") + os.pathsep + clean_environment.get("PATH", "")
            clean_environment["PYTHONNOUSERSITE"] = "1"
            for command_id, arguments in self.VERIFICATIONS:
                record, _, _ = self._runner.run(command_id, [str(python), *arguments], source, clean_environment)
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
        CleanEnvironmentReportValidator().validate(payload)
        return payload


class CleanEnvironmentReportValidator:
    """Validate the complete internal command and digest contract."""

    SETUP_COMMANDS = ("conda-create", "pip-install", "git-clone", "git-checkout")
    INVENTORY_COMMANDS = ("conda-explicit", "pip-freeze")

    @classmethod
    def expected_command_ids(cls) -> tuple[str, ...]:
        return (*cls.SETUP_COMMANDS, *(item[0] for item in CleanEnvironmentAttestor.VERIFICATIONS), *cls.INVENTORY_COMMANDS)

    def validate(self, payload: dict) -> None:
        if payload.get("schema_version") != "clean-environment-attestation-v1":
            raise ValueError("Unsupported clean-environment attestation schema")
        if not payload.get("all_commands_passed") or payload.get("verification_count") != len(CleanEnvironmentAttestor.VERIFICATIONS):
            raise ValueError("Clean-environment attestation is incomplete")
        commands = payload.get("commands", [])
        identifiers = tuple(command.get("command_id") for command in commands)
        if identifiers != self.expected_command_ids():
            raise ValueError("Clean-environment command ledger mismatch")
        for command in commands:
            if command.get("exit_code") != 0 or not command.get("argv"):
                raise ValueError("Clean-environment command did not pass")
            for field in ("stdout_sha256", "stderr_sha256"):
                self._require_digest(command.get(field), field)
        for field in (
            "source_tree_sha256",
            "lockfile_sha256",
            "pip_requirements_sha256",
            "conda_explicit_sha256",
            "pip_freeze_sha256",
        ):
            self._require_digest(payload.get(field), field)

    @staticmethod
    def _require_digest(value, field: str) -> None:
        if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"Clean-environment {field} is not a SHA-256 digest")


class CleanEnvironmentAttestationPolicy:
    """Fail closed when an internally valid report is stale for the release."""

    def __init__(
        self,
        repository: Path,
        lockfile: Path,
        pip_requirements: Path,
        allowed_post_attestation_paths: tuple[Path, ...],
        tree_hasher: CommittedSourceTreeHasher | None = None,
    ) -> None:
        self._repository = repository.resolve()
        self._lockfile = lockfile.resolve()
        self._pip_requirements = pip_requirements.resolve()
        self._allowed_paths = frozenset(path.as_posix() for path in allowed_post_attestation_paths)
        self._tree_hasher = tree_hasher or CommittedSourceTreeHasher()

    def validate(self, payload: dict) -> None:
        commit = payload["source_commit"]
        ancestry = subprocess.run(
            ("git", "merge-base", "--is-ancestor", commit, "HEAD"),
            cwd=self._repository,
            check=False,
        )
        if ancestry.returncode != 0:
            raise ValueError("Clean-environment source commit is not an ancestor of HEAD")
        changed = subprocess.run(
            ("git", "diff", "--name-only", f"{commit}..HEAD"),
            cwd=self._repository,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        unexpected = sorted(set(changed) - self._allowed_paths)
        if unexpected:
            raise ValueError(f"Clean-environment attestation is stale for committed path: {unexpected[0]}")
        if self._tree_hasher.digest(self._repository, commit) != payload["source_tree_sha256"]:
            raise ValueError("Clean-environment committed source tree hash mismatch")
        self._require_current_hash(self._lockfile, payload["lockfile_sha256"], "lockfile")
        self._require_current_hash(self._pip_requirements, payload["pip_requirements_sha256"], "pip requirements")

    @staticmethod
    def _require_current_hash(path: Path, expected: str, label: str) -> None:
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Clean-environment current {label} hash mismatch")
