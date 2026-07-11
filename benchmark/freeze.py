"""Freeze a generated benchmark suite into an auditable dataset directory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmark.generator import generate_benchmark_suite


def freeze_benchmark(root: str | Path, seed: int, feasible_count: int, infeasible_count: int) -> Path:
    destination = Path(root)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Benchmark destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    instances_dir = destination / "instances"
    instances_dir.mkdir()
    instances = generate_benchmark_suite(seed, feasible_count, infeasible_count)
    records = []
    for instance in instances:
        payload = json.dumps(instance.to_json(), indent=2, sort_keys=True) + "\n"
        path = instances_dir / f"{instance.instance_id}.json"
        path.write_text(payload)
        records.append({"instance_id": instance.instance_id, "sha256": hashlib.sha256(payload.encode()).hexdigest()})
    index = {
        "dataset_id": "compound-v1",
        "seed": seed,
        "feasible_count": feasible_count,
        "infeasible_count": infeasible_count,
        "instance_count": len(instances),
        "instances": records,
    }
    index_path = destination / "index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return index_path
