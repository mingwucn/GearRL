"""Frozen-budget, multi-seed comparison of requirements-first solver factories."""

from __future__ import annotations

import json
from importlib.metadata import version
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from benchmark.curated import FrozenCuratedDataset
from benchmark.specification import SolverBenchmarkView
from evaluation.blind_synthesis import BlindAdjudicator, BlindPredictionStore, BlindSynthesisExperiment
from synthesis.requirements_solver import (
    CpSatCompoundSynthesizer,
    EnumerativeCompoundSynthesizer,
    EvolutionaryCompoundSynthesizer,
    ProductionCandidateValidator,
    RequirementsFirstSynthesisSolver,
    SolverBudget,
)
from common.provenance import EnvironmentSpecificationFingerprint


class RequirementsSolverFactory(ABC):
    """Create isolated solver strategies under one frozen budget."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable method identifier used in result artifacts."""

    @abstractmethod
    def create(self, seed: int, budget: SolverBudget) -> RequirementsFirstSynthesisSolver:
        """Create one fresh solver for one independent run."""


class ExactEnumeratorFactory(RequirementsSolverFactory):
    @property
    def name(self) -> str:
        return "exact-enumerator"

    def create(self, seed: int, budget: SolverBudget) -> RequirementsFirstSynthesisSolver:
        return EnumerativeCompoundSynthesizer(ProductionCandidateValidator(), budget=budget)


class DifferentialEvolutionFactory(RequirementsSolverFactory):
    @property
    def name(self) -> str:
        return "differential-evolution"

    def create(self, seed: int, budget: SolverBudget) -> RequirementsFirstSynthesisSolver:
        return EvolutionaryCompoundSynthesizer(ProductionCandidateValidator(), budget)


class CpSatSolverFactory(RequirementsSolverFactory):
    @property
    def name(self) -> str:
        return "cp-sat"

    def create(self, seed: int, budget: SolverBudget) -> RequirementsFirstSynthesisSolver:
        return CpSatCompoundSynthesizer(ProductionCandidateValidator(), budget)


@dataclass(frozen=True)
class RequirementsComparisonProtocol:
    maximum_candidate_evaluations: int = 7000
    population_size: int = 12
    seeds: tuple[int, ...] = (2026, 2027, 2028, 2029, 2030)
    maximum_time_s: float = 10.0

    def __post_init__(self) -> None:
        if self.maximum_candidate_evaluations < 1 or self.population_size < 4 or not self.seeds or self.maximum_time_s <= 0:
            raise ValueError("Comparison protocol requires positive budgets and seeds")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Comparison seeds must be unique")

    def to_json(self) -> dict:
        return {
            "maximum_candidate_evaluations": self.maximum_candidate_evaluations,
            "population_size": self.population_size,
            "seeds": list(self.seeds),
            "maximum_time_s": self.maximum_time_s,
        }


class BlindRequirementsComparisonRunner:
    """Generate sealed method predictions without loading any truth records."""

    def __init__(self, factories: tuple[RequirementsSolverFactory, ...], protocol: RequirementsComparisonProtocol):
        if not factories or len({factory.name for factory in factories}) != len(factories):
            raise ValueError("Comparison requires uniquely named solver factories")
        self._factories = factories
        self._protocol = protocol

    def run(self, views: tuple[SolverBenchmarkView, ...], destination: str | Path) -> Path:
        root = Path(destination)
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("Blind comparison destination must be empty")
        root.mkdir(parents=True, exist_ok=True)
        records = []
        for factory in self._factories:
            seeds = self._protocol.seeds if factory.name == "differential-evolution" else self._protocol.seeds[:1]
            for seed in seeds:
                budget = SolverBudget(
                    self._protocol.maximum_candidate_evaluations,
                    seed,
                    self._protocol.population_size,
                    self._protocol.maximum_time_s,
                )
                predictions = BlindSynthesisExperiment(factory.create(seed, budget)).run(views)
                filename = f"{factory.name}-seed-{seed}.json"
                BlindPredictionStore().write(predictions, root / filename)
                records.append({"method": factory.name, "seed": seed, "predictions": filename})
        manifest = {
            "schema_version": "requirements-comparison-v2",
            "protocol": self._protocol.to_json(),
            "environment": {
                **EnvironmentSpecificationFingerprint().capture(("environment-ai.yml", "requirements-ai-pip.txt")),
                "ortools_version": version("ortools"),
                "scipy_version": version("scipy"),
            },
            "runs": records,
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest_path


class RequirementsComparisonAdjudicator:
    """Evaluate sealed comparison runs after the blind stage completes."""

    def adjudicate(self, dataset: FrozenCuratedDataset, comparison_root: str | Path) -> dict:
        root = Path(comparison_root)
        manifest = json.loads((root / "manifest.json").read_text())
        results = []
        for run in manifest["runs"]:
            path = root / run["predictions"]
            report = BlindAdjudicator().adjudicate(dataset, path)
            predictions = BlindPredictionStore().read(path)
            results.append(
                {
                    "method": run["method"],
                    "seed": run["seed"],
                    **report.to_json(),
                    "median_runtime_s": median(record["runtime_s"] for record in predictions),
                    "median_parameter_tuples": median(record["parameter_tuples_evaluated"] for record in predictions),
                    "complete_search_count": sum(bool(record["search_complete"]) for record in predictions),
                }
            )
        by_method = {}
        for method in sorted({result["method"] for result in results}):
            selected = [result for result in results if result["method"] == method]
            by_method[method] = {
                "run_count": len(selected),
                "accuracy_min": min(result["accuracy"] for result in selected),
                "accuracy_median": median(result["accuracy"] for result in selected),
                "decisive_coverage_min": min(result["decisive_coverage"] for result in selected),
                "decisive_accuracy_min": min(result["decisive_accuracy"] for result in selected),
                "median_runtime_s_across_runs": median(result["median_runtime_s"] for result in selected),
                "median_parameter_tuples_across_runs": median(result["median_parameter_tuples"] for result in selected),
            }
        return {
            "schema_version": "requirements-comparison-adjudication-v2",
            "dataset_id": dataset.dataset_id,
            "protocol": manifest["protocol"],
            "environment": manifest["environment"],
            "runs": results,
            "methods": by_method,
        }

    def write(self, report: dict, destination: str | Path) -> Path:
        path = Path(destination)
        if path.exists():
            raise FileExistsError(f"Comparison adjudication already exists: {path}")
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return path
