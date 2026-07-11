"""Persist a certified solver comparison on a hash-verified frozen benchmark."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from benchmark.loader import FrozenBenchmarkLoader
from common.provenance import RunBundleStore
from evaluation.comparison import CertifiedSolverComparison
from reporting.publication import PublicationReportGenerator
from synthesis.baselines import BranchAndBoundSolver, RandomizedSearchSolver, RouteFirstSolver


class FrozenSolverComparisonRunner:
    """Run predeclared solver strategies and persist only derived evidence."""
    def __init__(self, output_root: Path):
        self._store = RunBundleStore(output_root, repository_root=Path(__file__).parent, environment_file=Path(__file__).parent / "environment-ai.yml")

    def run(self, dataset_root: Path, seed: int = 2026) -> Path:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset_root)
        solvers = {"branch-and-bound": BranchAndBoundSolver(), "route-first": RouteFirstSolver(), "random-32": RandomizedSearchSolver(seed)}
        outcomes = CertifiedSolverComparison().evaluate(instances, solvers)
        bundle, _ = self._store.create(random_seed=seed, dataset_id=dataset_id, dataset_hash=dataset_hash, config={"methods": list(solvers), "random_attempts": 32}, model_version="certified-planar-v1")
        for outcome in outcomes:
            self._store.write_result(bundle, f"{outcome.solver_name}--{outcome.instance_id}", asdict(outcome))
        reporter = PublicationReportGenerator()
        summaries = reporter.summarize(outcomes, 1_000, seed)
        (bundle / "solver_table.md").write_text(reporter.to_markdown(summaries))
        (bundle / "solver_summary.json").write_text(json.dumps([asdict(item) for item in summaries], indent=2, sort_keys=True) + "\n")
        return bundle
