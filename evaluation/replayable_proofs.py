"""Replayable negative-proof study for the solver-hidden curated benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from benchmark import CuratedBenchmarkLoader, OracleProof, ReplayableExactCompoundTrainOracle, ReplayableOracleProofVerifier, SolverInputDirectoryLoader


@dataclass(frozen=True)
class ReplayableProofRecord:
    instance_id: str
    proof: OracleProof

    def to_json(self) -> dict:
        return {"instance_id": self.instance_id, "proof": self.proof.to_json()}


class ReplayableProofStudy:
    """Generate proofs only for evaluator-declared negative cases."""

    SCHEMA_VERSION = "replayable-negative-proofs-v1"

    def run(self, dataset_root: Path) -> dict:
        frozen = CuratedBenchmarkLoader().load(dataset_root)
        views = SolverInputDirectoryLoader().load(dataset_root / "solver-inputs")
        evidence = {payload["instance_id"]: payload for payload in frozen.evidence_payloads}
        records = []
        for view in views:
            if evidence[view.instance_id]["expected_feasible"]:
                continue
            proof = ReplayableExactCompoundTrainOracle().solve(view).proof
            ReplayableOracleProofVerifier().verify(view, proof)
            records.append(ReplayableProofRecord(view.instance_id, proof))
        return {
            "schema_version": self.SCHEMA_VERSION,
            "dataset_id": json.loads((dataset_root / "index.json").read_text())["dataset_id"],
            "dataset_sha256": frozen.dataset_sha256,
            "negative_case_count": len(records),
            "all_replayed": True,
            "records": [record.to_json() for record in records],
        }


class ReplayableProofPopulationContract:
    """Require one complete negative proof for every declared negative subject."""

    def expected_negative_ids(self, frozen) -> set[str]:
        return {
            payload["instance_id"]
            for payload in frozen.evidence_payloads
            if not payload["expected_feasible"]
        }

    def validate_records(self, records: list[dict], frozen) -> dict[str, OracleProof]:
        expected = self.expected_negative_ids(frozen)
        identifiers = [record["instance_id"] for record in records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Replayable-proof records contain duplicate subjects")
        actual = set(identifiers)
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise ValueError(
                f"Replayable-proof negative subject coverage mismatch; missing={missing}, unexpected={unexpected}"
            )
        proofs = {record["instance_id"]: OracleProof.from_json(record["proof"]) for record in records}
        for instance_id, proof in proofs.items():
            if proof.feasible:
                raise ValueError(f"Replayable proof is not infeasible: {instance_id}")
            if not proof.design_space_complete:
                raise ValueError(f"Replayable proof is not complete: {instance_id}")
        return proofs


class ReplayableProofEvidenceStore:
    """Persist and semantically verify replayable negative-proof evidence."""

    def __init__(self, population_contract: ReplayableProofPopulationContract | None = None) -> None:
        self._population_contract = population_contract or ReplayableProofPopulationContract()

    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, summary: dict, dataset_root: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Replayable-proof destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        summary_bytes = self._encode(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        index = dataset_root / "index.json"
        manifest = {
            "schema_version": "replayable-negative-proofs-artifact-v1",
            "dataset_root": str(dataset_root),
            "dataset_index_sha256": sha256(index.read_bytes()).hexdigest(),
            "dataset_sha256": summary["dataset_sha256"],
            "summary_sha256": sha256(summary_bytes).hexdigest(),
        }
        path = destination / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        summary_bytes = (destination / "summary.json").read_bytes()
        if sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Replayable-proof summary hash mismatch")
        dataset_root = Path(manifest["dataset_root"])
        if sha256((dataset_root / "index.json").read_bytes()).hexdigest() != manifest["dataset_index_sha256"]:
            raise ValueError("Replayable-proof dataset hash mismatch")
        frozen = CuratedBenchmarkLoader().load(dataset_root)
        if frozen.dataset_sha256 != manifest["dataset_sha256"]:
            raise ValueError("Replayable-proof curated payload digest mismatch")
        summary = json.loads(summary_bytes)
        if summary["dataset_sha256"] != frozen.dataset_sha256:
            raise ValueError("Replayable-proof summary dataset digest mismatch")
        views = {view.instance_id: view for view in SolverInputDirectoryLoader().load(dataset_root / "solver-inputs")}
        proofs = self._population_contract.validate_records(summary["records"], frozen)
        if len(proofs) != summary["negative_case_count"]:
            raise ValueError("Replayable-proof record cardinality mismatch")
        for instance_id, proof in proofs.items():
            ReplayableOracleProofVerifier().verify(views[instance_id], proof)
        if not summary["all_replayed"]:
            raise ValueError("Replayable-proof study is not fully replayed")
        return manifest
