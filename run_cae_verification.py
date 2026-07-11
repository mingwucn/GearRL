#!/usr/bin/env python3
"""Persist numerical verification evidence for the owned plane-stress solver."""

from __future__ import annotations

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
        suite = PlaneStressVerificationSuite()
        patch = suite.patch_test()
        cantilever = suite.cantilever_convergence()
        gear = suite.gear_root_agreement(agreement_limit=0.25)
        bundle, _ = self._store.create(random_seed=2026, dataset_id="cae-verification-v1", dataset_hash="owned-analytical-cases-v1", config={"gear_agreement_limit": 0.25, "cantilever_divisions": [10, 20, 40]}, model_version="plane-stress-cst-v1")
        payload = {"patch_test": asdict(patch), "cantilever_convergence": asdict(cantilever), "gear_root_agreement": asdict(gear)}
        self._store.write_result(bundle, "verification-suite", payload)
        summary = {"patch_passed": patch.maximum_relative_error < 1e-10, "cantilever_converged": cantilever.relative_errors[-1] < 0.1 and cantilever.relative_errors[-1] < cantilever.relative_errors[0], "gear_agreement_passed": gear.gate_passed}
        (bundle / "verification_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        return bundle


if __name__ == "__main__":
    print(CAEVerificationRunner(Path("artifacts/runs")).run())
