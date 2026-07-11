"""Aggregate immutable raw results without accepting hand-authored metrics."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any


class ResultAggregator:
    """Build publication metrics strictly from immutable raw run records."""

    def aggregate(self, bundle: str | Path) -> dict[str, Any]:
        root = Path(bundle)
        manifest_path = root / "manifest.json"
        result_dir = root / "results"
        if not manifest_path.is_file() or not result_dir.is_dir():
            raise ValueError("A run bundle requires manifest.json and results/")
        manifest = json.loads(manifest_path.read_text())
        results = [json.loads(path.read_text()) for path in sorted(result_dir.glob("*.json"))]
        if not results:
            raise ValueError("Cannot aggregate an empty run bundle")
        ids = [result.get("instance_id") for result in results]
        if any(not instance_id for instance_id in ids) or len(ids) != len(set(ids)):
            raise ValueError("Raw result instance ids must be present and unique")
        expected_feasible = [result for result in results if result["expected_feasible"]]
        expected_infeasible = [result for result in results if not result["expected_feasible"]]
        successful_feasible = sum(bool(result["valid"]) for result in expected_feasible)
        rejected_infeasible = sum(not bool(result["valid"]) for result in expected_infeasible)
        runtimes = [float(result["runtime_s"]) for result in results]
        return {
            "run_id": manifest["run_id"],
            "dataset_id": manifest["dataset_id"],
            "dataset_hash": manifest["dataset_hash"],
            "model_version": manifest["model_version"],
            "instance_count": len(results),
            "feasible_count": len(expected_feasible),
            "infeasible_count": len(expected_infeasible),
            "feasible_solution_rate": successful_feasible / len(expected_feasible) if expected_feasible else None,
            "infeasible_rejection_rate": rejected_infeasible / len(expected_infeasible) if expected_infeasible else None,
            "classification_accuracy": sum(bool(result["correct_classification"]) for result in results) / len(results),
            "median_runtime_s": median(runtimes),
        }


    def write(self, bundle: str | Path) -> Path:
        root = Path(bundle)
        destination = root / "summary.json"
        destination.write_text(json.dumps(self.aggregate(root), indent=2, sort_keys=True) + "\n")
        return destination
