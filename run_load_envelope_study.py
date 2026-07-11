#!/usr/bin/env python3
"""Run and freeze the sourced static load-envelope study."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from benchmark.loader import FrozenBenchmarkLoader
from evaluation.load_envelope import AEIStaticEnvelopeCatalog, LoadEnvelopeStudy


@dataclass(frozen=True)
class LoadEnvelopeConfig:
    sample_size: int = 24
    minimum_safety_factor: float = 1.0
    random_seed: int = 2026


class LoadEnvelopeEvidenceStore:
    """Write and verify deterministic, hash-addressed envelope evidence."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def write(self, root: Path, dataset_id: str, dataset_hash: str, config: LoadEnvelopeConfig, outcomes) -> Path:
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("Load-envelope destination must be empty")
        records = root / "records"
        records.mkdir(parents=True, exist_ok=True)
        index = []
        for outcome in outcomes:
            payload = self._encode(asdict(outcome))
            (records / f"{outcome.case_id}.json").write_bytes(payload)
            index.append({"case_id": outcome.case_id, "sha256": hashlib.sha256(payload).hexdigest()})
        summary = {
            "case_count": len(outcomes),
            "layout_case_count": sum(len(item.layout_outcomes) for item in outcomes),
            "fully_valid_case_count": sum(item.valid_fraction == 1.0 for item in outcomes),
            "minimum_safety_factor": min(item.minimum_safety_factor for item in outcomes),
        }
        summary_bytes = self._encode(summary)
        (root / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "study_scope": "digital static elastic tooth-root bending screen; not fatigue, contact, or qualification",
            "model_version": "certified-planar-v3+involute-tooth-root-plane-stress-v3",
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "config": asdict(config),
            "materials": [asdict(item) for item in AEIStaticEnvelopeCatalog.materials()],
            "summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "records": index,
        }
        (root / "manifest.json").write_bytes(self._encode(manifest))
        return root / "manifest.json"

    def load(self, root: Path) -> tuple[dict, dict, tuple[dict, ...]]:
        manifest = json.loads((root / "manifest.json").read_bytes())
        summary_bytes = (root / "summary.json").read_bytes()
        if hashlib.sha256(summary_bytes).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Load-envelope summary hash mismatch")
        outcomes = []
        for item in manifest["records"]:
            payload = (root / "records" / f"{item['case_id']}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                raise ValueError(f"Load-envelope record hash mismatch: {item['case_id']}")
            outcomes.append(json.loads(payload))
        summary = json.loads(summary_bytes)
        if len(outcomes) != summary["case_count"]:
            raise ValueError("Load-envelope count mismatch")
        return manifest, summary, tuple(outcomes)


class LoadEnvelopeCommand:
    def run(self, dataset: Path, output: Path, config: LoadEnvelopeConfig) -> Path:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        outcomes = LoadEnvelopeStudy(config.minimum_safety_factor).evaluate(
            instances, AEIStaticEnvelopeCatalog().cases(), config.sample_size
        )
        return LoadEnvelopeEvidenceStore().write(output, dataset_id, dataset_hash, config, outcomes)


class LoadEnvelopeCLI:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--dataset", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--sample-size", type=int, default=24)
        args = parser.parse_args()
        print(LoadEnvelopeCommand().run(args.dataset, args.output, LoadEnvelopeConfig(args.sample_size)))


if __name__ == "__main__":
    LoadEnvelopeCLI().run()
