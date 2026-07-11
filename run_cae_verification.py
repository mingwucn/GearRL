#!/usr/bin/env python3
"""Persist numerical verification evidence for the owned plane-stress solver."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from cae.verification import PlaneStressVerificationSuite
from common.provenance import RunBundleStore


class CAEVerificationRunner:
    """Execute and persist patch, convergence, and analytical agreement checks."""

    def __init__(self, output_root: Path):
        self._store = RunBundleStore(output_root, repository_root=Path(__file__).parent, environment_file=Path(__file__).parent / "environment-ai.yml")

    def run(self) -> Path:
        payload, summary = CAEVerificationStudy().execute()
        bundle, _ = self._store.create(random_seed=2026, dataset_id="cae-verification-v3", dataset_hash="owned-analytical-cases-v3", config={"gear_agreement_limit": 0.25, "tooth_convergence_limit": 0.10, "cantilever_divisions": [10, 20, 40]}, model_version="involute-tooth-root-plane-stress-v3")
        self._store.write_result(bundle, "verification-suite", payload)
        (bundle / "verification_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


class CAEVerificationStudy:
    """Own the four preregistered numerical gates for the production CAE model."""

    def execute(self) -> tuple[dict, dict]:
        suite = PlaneStressVerificationSuite()
        patch = suite.patch_test()
        cantilever = suite.cantilever_convergence()
        gear = suite.gear_root_agreement(agreement_limit=0.25)
        tooth = suite.gear_tooth_convergence(convergence_limit=0.10)
        payload = {
            "patch_test": asdict(patch),
            "cantilever_convergence": asdict(cantilever),
            "gear_root_agreement": asdict(gear),
            "gear_tooth_convergence": asdict(tooth),
        }
        summary = {
            "patch_passed": patch.maximum_relative_error < 1e-10,
            "cantilever_converged": cantilever.relative_errors[-1] < 0.1 and cantilever.relative_errors[-1] < cantilever.relative_errors[0],
            "gear_agreement_passed": gear.gate_passed,
            "gear_tooth_convergence_passed": tooth.gate_passed,
        }
        return payload, summary


class FrozenCAEVerificationStore:
    """Write-once content-addressed evidence for publication review."""

    def write(self, destination: Path, payload: dict, summary: dict) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Frozen CAE verification destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        evidence_bytes = self._encode(payload)
        summary_bytes = self._encode(summary)
        (destination / "verification.json").write_bytes(evidence_bytes)
        (destination / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "dataset_id": "cae-verification-v3",
            "model_version": "involute-tooth-root-plane-stress-v3",
            "verification_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
            "summary_sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "all_gates_passed": all(summary.values()),
        }
        (destination / "manifest.json").write_bytes(self._encode(manifest))
        return destination / "manifest.json"

    @staticmethod
    def _encode(value: dict) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


class CAEVerificationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--frozen-output", type=Path)
        arguments = parser.parse_args()
        if arguments.frozen_output:
            payload, summary = CAEVerificationStudy().execute()
            print(FrozenCAEVerificationStore().write(arguments.frozen_output, payload, summary))
        else:
            print(CAEVerificationRunner(Path("artifacts/runs")).run())


if __name__ == "__main__":
    CAEVerificationCommand().run()
