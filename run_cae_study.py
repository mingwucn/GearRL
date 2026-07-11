#!/usr/bin/env python3
"""Persist a stratified static-strength screening study on frozen designs."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from common.design_models import MaterialLoadCase
from common.provenance import RunBundleStore
from evaluation.cae_study import StratifiedCAEStudy


@dataclass(frozen=True)
class FrozenCAEStudyConfig:
    """Immutable declaration of the digital static-strength experiment."""

    sample_size: int = 120
    minimum_safety_factor: float = 1.0
    random_seed: int = 2026


class FrozenCAEStudyRunner:
    """Run declared CAE screening and retain immutable per-layout evidence."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(
            output_root,
            repository_root=Path(__file__).parent,
            environment_file=Path(__file__).parent / "environment-ai.yml",
        )

    def run(self, dataset_root: Path, config: FrozenCAEStudyConfig | None = None) -> Path:
        config = config or FrozenCAEStudyConfig()
        if config.sample_size < 1 or config.minimum_safety_factor <= 0:
            raise ValueError("CAE sample size and minimum safety factor must be positive")
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        load_case = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
        outcomes = StratifiedCAEStudy(load_case, config.minimum_safety_factor).evaluate(instances, config.sample_size)
        bundle, _ = self._store.create(
            random_seed=config.random_seed,
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            config={**asdict(config), "load_case": asdict(load_case)},
            model_version="certified-planar-v2+involute-tooth-root-plane-stress-v3",
        )
        for outcome in outcomes:
            self._store.write_result(bundle, outcome.instance_id, asdict(outcome))
        safety = [item.minimum_safety_factor for item in outcomes if item.minimum_safety_factor is not None]
        summary = {
            "observations": len(outcomes),
            "valid_count": sum(item.valid for item in outcomes),
            "minimum_safety_factor": min(safety) if safety else None,
        }
        (bundle / "cae_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


class FrozenCAEStudyEvidenceStore:
    """Persist deterministic per-layout v3 evidence for publication review."""

    def write(
        self,
        destination: Path,
        dataset_id: str,
        dataset_hash: str,
        config: FrozenCAEStudyConfig,
        load_case: MaterialLoadCase,
        outcomes,
    ) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Frozen CAE study destination must be empty")
        records_root = destination / "records"
        records_root.mkdir(parents=True, exist_ok=True)
        records = []
        for outcome in outcomes:
            payload = self._encode(asdict(outcome))
            (records_root / f"{outcome.instance_id}.json").write_bytes(payload)
            records.append({"instance_id": outcome.instance_id, "sha256": hashlib.sha256(payload).hexdigest()})
        safety = [item.minimum_safety_factor for item in outcomes if item.minimum_safety_factor is not None]
        summary = {
            "observations": len(outcomes),
            "valid_count": sum(item.valid for item in outcomes),
            "minimum_safety_factor": min(safety) if safety else None,
            "report_count": sum(item.report_count for item in outcomes),
        }
        summary_bytes = self._encode(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "model_version": "certified-planar-v2+involute-tooth-root-plane-stress-v3",
            "config": asdict(config),
            "load_case": asdict(load_case),
            "summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "records": records,
        }
        (destination / "manifest.json").write_bytes(self._encode(manifest))
        return destination / "manifest.json"

    @staticmethod
    def _encode(value: dict) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


class FrozenCAEStudyEvidenceLoader:
    """Verify frozen record hashes, summary counts, and embedded v3 reports."""

    def load(self, root: Path) -> tuple[dict, dict, tuple[dict, ...]]:
        manifest = json.loads((root / "manifest.json").read_bytes())
        summary_bytes = (root / "summary.json").read_bytes()
        if hashlib.sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Frozen CAE summary hash mismatch")
        summary = json.loads(summary_bytes)
        outcomes = []
        for record in manifest["records"]:
            payload = (root / "records" / f"{record['instance_id']}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                raise ValueError(f"Frozen CAE record hash mismatch: {record['instance_id']}")
            outcome = json.loads(payload)
            if any(report["model_version"] != "involute-tooth-root-plane-stress-v3" for report in outcome["reports"]):
                raise ValueError(f"Unexpected CAE report version: {record['instance_id']}")
            outcomes.append(outcome)
        if len(outcomes) != summary["observations"] or sum(outcome["report_count"] for outcome in outcomes) != summary["report_count"]:
            raise ValueError("Frozen CAE study counts do not match")
        return manifest, summary, tuple(outcomes)


class FrozenCAEStudyCommand:
    """Compose loading, stratified v3 analysis, and deterministic persistence."""

    def run(self, dataset_root: Path, destination: Path, config: FrozenCAEStudyConfig) -> Path:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        load_case = MaterialLoadCase("steel", 1.0, 10.0, 210_000.0, 0.3, 800.0)
        outcomes = StratifiedCAEStudy(load_case, config.minimum_safety_factor).evaluate(instances, config.sample_size)
        return FrozenCAEStudyEvidenceStore().write(
            destination,
            dataset_id,
            dataset_hash,
            config,
            load_case,
            outcomes,
        )


class CAEStudyCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--dataset", type=Path, required=True)
        parser.add_argument("--output-root", type=Path, default=Path("artifacts/runs"))
        parser.add_argument("--frozen-output", type=Path)
        parser.add_argument("--sample-size", type=int, default=120)
        args = parser.parse_args()
        config = FrozenCAEStudyConfig(sample_size=args.sample_size)
        if args.frozen_output:
            print(FrozenCAEStudyCommand().run(args.dataset, args.frozen_output, config))
        else:
            print(FrozenCAEStudyRunner(args.output_root).run(args.dataset, config))


if __name__ == "__main__":
    CAEStudyCommand().run()
