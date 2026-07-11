#!/usr/bin/env python3
"""Run and freeze the paired static-strength synthesis ablation."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark import SolverInputDirectoryLoader
from common.design_models import MaterialLoadCase
from evaluation.strength_coupled import StrengthCoupledSynthesisStudy, StrengthCouplingRequirements
from synthesis import EnumerativeCompoundSynthesizer, ProductionCandidateValidator


@dataclass(frozen=True)
class StrengthCoupledStudyConfig:
    case_ids: tuple[str, ...] = (
        "valid-unit-30", "valid-up-32", "valid-down-34", "valid-high-35", "valid-low-31",
        "valid-five-four-36", "valid-three-four-33", "valid-four-three-37",
        "valid-nine-ten-30", "valid-eleven-ten-38",
    )
    minimum_safety_factor: float = 2.3
    material_name: str = "S355 (plate)"
    input_torque_nm: float = 1.0
    face_width_mm: float = 8.0
    youngs_modulus_mpa: float = 210_000.0
    poisson_ratio: float = 0.3
    allowable_stress_mpa: float = 355.0 / 1.5
    efficiency: float = 0.98

    @property
    def requirements(self) -> StrengthCouplingRequirements:
        return StrengthCouplingRequirements(
            MaterialLoadCase(
                self.material_name,
                self.input_torque_nm,
                self.face_width_mm,
                self.youngs_modulus_mpa,
                self.poisson_ratio,
                self.allowable_stress_mpa,
                self.efficiency,
            ),
            self.minimum_safety_factor,
        )


class PredeclaredSolverViewRepository:
    """Select a frozen ID list from hash-checked blind solver inputs."""

    def load(self, dataset_root: Path, case_ids: tuple[str, ...]):
        index_path = dataset_root / "index.json"
        index = json.loads(index_path.read_text())
        hashes = {item["instance_id"]: item["solver_sha256"] for item in index["instances"]}
        if len(case_ids) != len(set(case_ids)) or any(case_id not in hashes for case_id in case_ids):
            raise ValueError("Coupling case IDs must be unique members of the frozen dataset")
        for case_id in case_ids:
            payload = (dataset_root / "solver-inputs" / f"{case_id}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != hashes[case_id]:
                raise ValueError(f"Coupling solver-input hash mismatch: {case_id}")
        all_views = {view.instance_id: view for view in SolverInputDirectoryLoader().load(dataset_root / "solver-inputs")}
        return index_path, tuple(all_views[case_id] for case_id in case_ids)


class StrengthCoupledEvidenceStore:
    """Persist hash-addressed paired outcomes and a derived classification summary."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def write(self, root: Path, index_path: Path, config: StrengthCoupledStudyConfig, outcomes) -> Path:
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("Strength-coupling destination must be empty")
        records_root = root / "records"
        records_root.mkdir(parents=True, exist_ok=True)
        records = []
        for outcome in outcomes:
            payload = self._encode(asdict(outcome))
            (records_root / f"{outcome.instance_id}.json").write_bytes(payload)
            records.append({"instance_id": outcome.instance_id, "sha256": hashlib.sha256(payload).hexdigest()})
        summary = {
            "case_count": len(outcomes),
            "retained_count": sum(item.classification == "retained" for item in outcomes),
            "redesigned_count": sum(item.classification == "redesigned" for item in outcomes),
            "rejected_count": sum(item.classification == "rejected" for item in outcomes),
            "baseline_strength_admissible_count": sum(item.baseline_admissible_under_strength for item in outcomes),
        }
        summary_bytes = self._encode(summary)
        (root / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "scope": "paired requirements-first synthesis with and without static tooth-root admission",
            "model_version": "requirements-first-v1+certified-planar-v3+involute-tooth-root-plane-stress-v3",
            "config": asdict(config),
            "source_index": str(index_path),
            "source_index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
            "summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "records": records,
        }
        (root / "manifest.json").write_bytes(self._encode(manifest))
        return root / "manifest.json"

    def load(self, root: Path) -> tuple[dict, dict, tuple[dict, ...]]:
        manifest = json.loads((root / "manifest.json").read_text())
        source = Path(manifest["source_index"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_index_sha256"]:
            raise ValueError("Strength-coupling source index hash mismatch")
        summary_bytes = (root / "summary.json").read_bytes()
        if hashlib.sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Strength-coupling summary hash mismatch")
        records = []
        for item in manifest["records"]:
            payload = (root / "records" / f"{item['instance_id']}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise ValueError(f"Strength-coupling record hash mismatch: {item['instance_id']}")
            records.append(json.loads(payload))
        summary = json.loads(summary_bytes)
        if len(records) != summary["case_count"]:
            raise ValueError("Strength-coupling record count mismatch")
        return manifest, summary, tuple(records)


class StrengthCoupledStudyCommand:
    def run(self, dataset: Path, output: Path, config: StrengthCoupledStudyConfig) -> Path:
        index_path, views = PredeclaredSolverViewRepository().load(dataset, config.case_ids)
        validator = ProductionCandidateValidator()
        outcomes = StrengthCoupledSynthesisStudy(
            EnumerativeCompoundSynthesizer(validator), validator, config.requirements
        ).evaluate(views)
        return StrengthCoupledEvidenceStore().write(output, index_path, config, outcomes)


class StrengthCoupledStudyCLI:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--dataset", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args()
        print(StrengthCoupledStudyCommand().run(args.dataset, args.output, StrengthCoupledStudyConfig()))


if __name__ == "__main__":
    StrengthCoupledStudyCLI().run()
