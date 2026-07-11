"""Evidence-bound AEI submission-readiness auditing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from reproducibility.clean_environment import CleanEnvironmentAttestationPolicy, CleanEnvironmentEvidenceStore


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    description: str
    evidence_path: Path | None
    check_type: str
    expected: Any = None
    pointer: str | None = None
    status_if_satisfied: str = "passed"


@dataclass(frozen=True)
class EvidenceFinding:
    requirement_id: str
    description: str
    status: str
    observed: Any
    evidence_path: str | None
    evidence_sha256: str | None


class EvidenceCheck(ABC):
    """Strategy contract for one authoritative evidence check."""

    @abstractmethod
    def observe(self, requirement: EvidenceRequirement) -> Any:
        raise NotImplementedError


class FileExistsCheck(EvidenceCheck):
    def observe(self, requirement: EvidenceRequirement) -> bool:
        return bool(requirement.evidence_path and requirement.evidence_path.is_file())


class TextContainsCheck(EvidenceCheck):
    def observe(self, requirement: EvidenceRequirement) -> bool:
        assert requirement.evidence_path is not None
        return str(requirement.pointer).lower() in requirement.evidence_path.read_text().lower()


class JsonPointerCheck(EvidenceCheck):
    def observe(self, requirement: EvidenceRequirement) -> Any:
        assert requirement.evidence_path is not None
        value: Any = json.loads(requirement.evidence_path.read_text())
        for token in (requirement.pointer or "").strip("/").split("/"):
            if token:
                value = value[int(token)] if isinstance(value, list) else value[token]
        return value


class RegistryCountCheck(EvidenceCheck):
    def observe(self, requirement: EvidenceRequirement) -> dict[str, int]:
        assert requirement.evidence_path is not None
        payload = json.loads(requirement.evidence_path.read_text())
        return {"tables": len(payload["tables"]), "figures": len(payload["figures"])}


class JsonLengthCheck(EvidenceCheck):
    def observe(self, requirement: EvidenceRequirement) -> int:
        value = JsonPointerCheck().observe(requirement)
        return len(value)


class BenchmarkIntegrityCheck(EvidenceCheck):
    """Verify every frozen benchmark member against its index hash."""

    def observe(self, requirement: EvidenceRequirement) -> dict[str, Any]:
        assert requirement.evidence_path is not None
        index = json.loads(requirement.evidence_path.read_text())
        instance_root = requirement.evidence_path.parent / "instances"
        valid = 0
        for item in index["instances"]:
            path = instance_root / f"{item['instance_id']}.json"
            if path.is_file() and sha256(path.read_bytes()).hexdigest() == item["sha256"]:
                valid += 1
        return {"declared": index["instance_count"], "hash_valid": valid}


class CuratedIntegrityCheck(EvidenceCheck):
    """Verify physical separation and hashes of solver/evaluator benchmark views."""

    def observe(self, requirement: EvidenceRequirement) -> dict[str, Any]:
        assert requirement.evidence_path is not None
        index = json.loads(requirement.evidence_path.read_text())
        root = requirement.evidence_path.parent
        valid = 0
        separated = True
        for item in index["instances"]:
            solver = root / "solver-inputs" / f"{item['instance_id']}.json"
            evaluator = root / "evaluator-only" / f"{item['instance_id']}.json"
            separated &= solver.parent != evaluator.parent
            if (
                sha256(solver.read_bytes()).hexdigest() == item["solver_sha256"]
                and sha256(evaluator.read_bytes()).hexdigest() == item["evidence_sha256"]
            ):
                valid += 1
        return {"declared": index["instance_count"], "hash_valid": valid, "separated": separated}


class CleanAttestationCheck(EvidenceCheck):
    """Require an internally valid attestation that is fresh for the release tree."""

    def observe(self, requirement: EvidenceRequirement) -> bool:
        assert requirement.evidence_path is not None
        try:
            payload = CleanEnvironmentEvidenceStore().verify(requirement.evidence_path.parent)
            CleanEnvironmentAttestationPolicy(
                Path("."),
                Path("environment-ai.lock"),
                Path("requirements-ai-pip.txt"),
                (
                    Path("data/results/clean-environment-v2/manifest.json"),
                    Path("data/results/clean-environment-v2/report.json"),
                    Path("paper/submission-readiness-v2/manifest.json"),
                    Path("paper/submission-readiness-v2/report.json"),
                ),
            ).validate(payload)
        except (FileNotFoundError, KeyError, RuntimeError, ValueError):
            return False
        return True


class EvidenceCheckFactory:
    """Construct check strategies from validated declarative names."""

    _CHECKS = {
        "file_exists": FileExistsCheck,
        "text_contains": TextContainsCheck,
        "json_pointer": JsonPointerCheck,
        "json_length": JsonLengthCheck,
        "registry_count": RegistryCountCheck,
        "benchmark_integrity": BenchmarkIntegrityCheck,
        "curated_integrity": CuratedIntegrityCheck,
        "clean_attestation": CleanAttestationCheck,
    }

    def create(self, check_type: str) -> EvidenceCheck:
        try:
            return self._CHECKS[check_type]()
        except KeyError as error:
            raise ValueError(f"Unsupported evidence check: {check_type}") from error


class SubmissionReadinessAuditor:
    """Evaluate all declared gates and refuse submission on unresolved blockers."""

    def __init__(self, factory: EvidenceCheckFactory | None = None) -> None:
        self._factory = factory or EvidenceCheckFactory()

    @staticmethod
    def _requirement(payload: dict[str, Any]) -> EvidenceRequirement:
        evidence = payload.get("evidence_path")
        return EvidenceRequirement(
            requirement_id=payload["requirement_id"],
            description=payload["description"],
            evidence_path=Path(evidence) if evidence else None,
            check_type=payload["check_type"],
            expected=payload.get("expected"),
            pointer=payload.get("pointer"),
            status_if_satisfied=payload.get("status_if_satisfied", "passed"),
        )

    def audit(self, source: Path) -> dict[str, Any]:
        declaration = json.loads(source.read_text())
        if declaration["schema_version"] != "aei-submission-readiness-source-v1":
            raise ValueError("Unsupported readiness source schema")
        findings = []
        for payload in declaration["requirements"]:
            requirement = self._requirement(payload)
            path = requirement.evidence_path
            observed = self._factory.create(requirement.check_type).observe(requirement)
            satisfied = observed == requirement.expected
            status = requirement.status_if_satisfied if satisfied else "failed"
            findings.append(
                EvidenceFinding(
                    requirement.requirement_id,
                    requirement.description,
                    status,
                    observed,
                    str(path) if path else None,
                    sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None,
                )
            )
        counts = {status: sum(item.status == status for item in findings) for status in ("passed", "partial", "external_pending", "failed")}
        blockers = [item.requirement_id for item in findings if item.status in {"failed", "external_pending"}]
        return {
            "schema_version": "aei-submission-readiness-report-v1",
            "target": declaration["target"],
            "assessment_scope": declaration["assessment_scope"],
            "ready_to_submit": not blockers,
            "status_counts": counts,
            "blocking_requirements": blockers,
            "findings": [item.__dict__ for item in findings],
        }


class SubmissionReadinessArtifactStore:
    """Persist and byte-reproduce the readiness assessment."""

    @staticmethod
    def _encode(payload: Any) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def build(self, source: Path, output: Path) -> Path:
        if output.exists() and any(output.iterdir()):
            raise FileExistsError("Readiness destination must be empty")
        output.mkdir(parents=True, exist_ok=True)
        report = SubmissionReadinessAuditor().audit(source)
        report_bytes = self._encode(report)
        (output / "report.json").write_bytes(report_bytes)
        manifest = {
            "schema_version": "aei-submission-readiness-artifact-v1",
            "source": str(source),
            "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "report_sha256": sha256(report_bytes).hexdigest(),
        }
        path = output / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, root: Path) -> dict[str, Any]:
        manifest = json.loads((root / "manifest.json").read_text())
        source = Path(manifest["source"])
        if sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise ValueError("Readiness source hash mismatch")
        report = (root / "report.json").read_bytes()
        if sha256(report).hexdigest() != manifest["report_sha256"]:
            raise ValueError("Readiness report hash mismatch")
        return json.loads(report)

    def verify_reproduction(self, frozen: Path) -> None:
        manifest = json.loads((frozen / "manifest.json").read_text())
        self.verify(frozen)
        with TemporaryDirectory(prefix="gearrl-readiness-") as temporary:
            generated = Path(temporary)
            self.build(Path(manifest["source"]), generated)
            frozen_files = {path.name: path.read_bytes() for path in frozen.iterdir() if path.is_file()}
            generated_files = {path.name: path.read_bytes() for path in generated.iterdir() if path.is_file()}
            if frozen_files != generated_files:
                raise ValueError("Regenerated readiness assessment is not byte-identical")
