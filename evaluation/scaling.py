"""Predeclared scaling and anytime evaluation for requirements-first solvers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
import platform
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter

from benchmark.oracle import ExactCompoundTrainOracle
from benchmark.specification import PrescribedShaft, SolverBenchmarkView
from common.design_models import Point2D
from evaluation.requirements_comparison import RequirementsSolverFactory
from common.provenance import EnvironmentSpecificationFingerprint
from synthesis.requirements_solver import SolverBudget


@dataclass(frozen=True)
class ScalingProtocol:
    tooth_domain_sizes: tuple[int, ...] = (5, 9, 13, 17)
    candidate_budgets: tuple[int, ...] = (250, 1_000, 7_000, 100_000)
    stochastic_seeds: tuple[int, ...] = tuple(range(2026, 2056))
    minimum_teeth: int = 18
    population_size: int = 12
    maximum_time_s: float = 10.0

    def __post_init__(self) -> None:
        if any(size < 2 for size in self.tooth_domain_sizes) or tuple(sorted(set(self.tooth_domain_sizes))) != self.tooth_domain_sizes:
            raise ValueError("Tooth-domain sizes must be unique, increasing, and at least two")
        if any(value < 1 for value in self.candidate_budgets) or tuple(sorted(set(self.candidate_budgets))) != self.candidate_budgets:
            raise ValueError("Candidate budgets must be unique, increasing, and positive")
        if len(self.stochastic_seeds) < 2 or len(set(self.stochastic_seeds)) != len(self.stochastic_seeds):
            raise ValueError("Scaling requires multiple unique stochastic seeds")


@dataclass(frozen=True)
class ScalingCase:
    view: SolverBenchmarkView
    tooth_domain_size: int
    family: str
    expected_feasible: bool
    oracle_proof: dict


class ScalingCaseFactory:
    """Derive blind scaling views from two frozen requirements templates."""

    def __init__(self, oracle: ExactCompoundTrainOracle | None = None):
        self._oracle = oracle or ExactCompoundTrainOracle()

    def create(self, templates: dict[str, SolverBenchmarkView], protocol: ScalingProtocol) -> tuple[ScalingCase, ...]:
        required = {"valid-unit-30", "valid-nine-ten-30"}
        if set(templates) != required:
            raise ValueError(f"Scaling templates must be exactly {sorted(required)}")
        cases = []
        for size in protocol.tooth_domain_sizes:
            maximum = protocol.minimum_teeth + size - 1
            variants = (
                (templates["valid-unit-30"], "unit-feasible", 1.0, None),
                (templates["valid-nine-ten-30"], "nine-ten-feasible", 0.9, None),
                (templates["valid-unit-30"], "irrational-ratio-infeasible", 1.41421356237, None),
                (templates["valid-unit-30"], "spacing-infeasible", 1.0, Point2D(100.0, 0.0)),
            )
            for template, family, ratio, output_center in variants:
                view = self._view(template, size, protocol.minimum_teeth, maximum, family, ratio, output_center)
                truth = self._oracle.solve(view)
                expected = family.endswith("feasible") and not family.endswith("infeasible")
                if truth.proof.feasible != expected or (not expected and not truth.proof.design_space_complete):
                    raise RuntimeError(f"Scaling truth construction failed: {view.instance_id}")
                cases.append(ScalingCase(view, size, family, expected, truth.proof.to_json()))
        return tuple(cases)

    @staticmethod
    def _view(
        template: SolverBenchmarkView,
        size: int,
        minimum: int,
        maximum: int,
        family: str,
        ratio: float,
        output_center: Point2D | None,
    ) -> SolverBenchmarkView:
        constraints = replace(
            template.specification.problem.constraints,
            min_teeth=minimum,
            max_teeth=maximum,
            target_speed_ratio=ratio,
            ratio_tolerance=1e-12,
        )
        problem = replace(template.specification.problem, constraints=constraints)
        shafts = template.specification.prescribed_shafts
        if output_center is not None:
            shafts = tuple(PrescribedShaft(shaft.role, output_center if shaft.role == "output" else shaft.center) for shaft in shafts)
        specification = replace(template.specification, problem=problem, prescribed_shafts=shafts)
        return SolverBenchmarkView(f"scale-{size:02d}-{family}", family, "scaling-test", specification)


@dataclass(frozen=True)
class ScalingObservation:
    instance_id: str
    family: str
    tooth_domain_size: int
    full_parameter_space: int
    candidate_budget: int
    method: str
    seed: int
    expected_feasible: bool
    predicted_feasible: bool
    correct_classification: bool
    search_complete: bool
    negative_proof: bool
    runtime_s: float
    parameter_tuples_evaluated: int
    placements_evaluated: int


class SolverScalingStudy:
    """Evaluate factories across fixed sizes, budgets, and stochastic seeds."""

    def __init__(self, factories: tuple[RequirementsSolverFactory, ...], protocol: ScalingProtocol):
        if not factories or len({factory.name for factory in factories}) != len(factories):
            raise ValueError("Scaling solver factories must have unique names")
        self._factories = factories
        self._protocol = protocol

    def evaluate(self, cases: tuple[ScalingCase, ...]) -> tuple[ScalingObservation, ...]:
        observations = []
        for budget_value in self._protocol.candidate_budgets:
            for factory in self._factories:
                seeds = self._protocol.stochastic_seeds if factory.name == "differential-evolution" else self._protocol.stochastic_seeds[:1]
                for seed in seeds:
                    budget = SolverBudget(budget_value, seed, self._protocol.population_size, self._protocol.maximum_time_s)
                    solver = factory.create(seed, budget)
                    for case in cases:
                        started = perf_counter()
                        result = solver.solve(case.view)
                        runtime = perf_counter() - started
                        predicted = result.train is not None
                        observations.append(
                            ScalingObservation(
                                case.view.instance_id,
                                case.family,
                                case.tooth_domain_size,
                                case.tooth_domain_size**4,
                                budget_value,
                                factory.name,
                                seed,
                                case.expected_feasible,
                                predicted,
                                predicted == case.expected_feasible,
                                result.search_complete,
                                not case.expected_feasible and not predicted and result.search_complete,
                                runtime,
                                result.parameter_tuples_evaluated,
                                result.placements_evaluated,
                            )
                        )
        return tuple(observations)


class ScalingSummaryBuilder:
    """Aggregate runs without hiding stochastic worst-case behavior."""

    def build(self, observations: tuple[ScalingObservation, ...]) -> list[dict]:
        groups: dict[tuple[str, int, int], list[ScalingObservation]] = {}
        for item in observations:
            groups.setdefault((item.method, item.tooth_domain_size, item.candidate_budget), []).append(item)
        summaries = []
        for (method, size, budget), records in sorted(groups.items()):
            by_seed: dict[int, list[ScalingObservation]] = {}
            for record in records:
                by_seed.setdefault(record.seed, []).append(record)
            seed_accuracy = [sum(item.correct_classification for item in run) / len(run) for run in by_seed.values()]
            seed_feasible = [
                sum(item.predicted_feasible for item in run if item.expected_feasible) /
                sum(item.expected_feasible for item in run)
                for run in by_seed.values()
            ]
            negative_records = [item for item in records if not item.expected_feasible]
            summaries.append(
                {
                    "method": method,
                    "tooth_domain_size": size,
                    "full_parameter_space": size**4,
                    "candidate_budget": budget,
                    "run_count": len(by_seed),
                    "accuracy_min": min(seed_accuracy),
                    "accuracy_median": median(seed_accuracy),
                    "feasible_recovery_min": min(seed_feasible),
                    "feasible_recovery_median": median(seed_feasible),
                    "negative_proof_rate": sum(item.negative_proof for item in negative_records) / len(negative_records),
                    "median_runtime_s": median(item.runtime_s for item in records),
                    "median_parameter_tuples": median(item.parameter_tuples_evaluated for item in records),
                }
            )
        return summaries


class ScalingEvidenceStore:
    """Persist raw scaling observations with source and result hashes."""

    @staticmethod
    def _encode(value) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    def write(
        self,
        root: Path,
        protocol: ScalingProtocol,
        template_index: Path,
        cases: tuple[ScalingCase, ...],
        observations: tuple[ScalingObservation, ...],
    ) -> Path:
        if root.exists() and any(root.iterdir()):
            raise FileExistsError("Scaling evidence destination must be empty")
        root.mkdir(parents=True, exist_ok=True)
        cases_bytes = self._encode([
            {
                "instance_id": case.view.instance_id,
                "family": case.family,
                "tooth_domain_size": case.tooth_domain_size,
                "expected_feasible": case.expected_feasible,
                "oracle_proof": case.oracle_proof,
                "solver_view": case.view.to_json(),
            }
            for case in cases
        ])
        records_bytes = self._encode([asdict(item) for item in observations])
        summary_bytes = self._encode(ScalingSummaryBuilder().build(observations))
        (root / "cases.json").write_bytes(cases_bytes)
        (root / "observations.json").write_bytes(records_bytes)
        (root / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "schema_version": "requirements-scaling-v1",
            "protocol": asdict(protocol),
            "template_index": str(template_index),
            "template_index_sha256": sha256(template_index.read_bytes()).hexdigest(),
            "runtime_environment": ScalingRuntimeFingerprint().capture(),
            "case_count": len(cases),
            "observation_count": len(observations),
            "cases_sha256": sha256(cases_bytes).hexdigest(),
            "observations_sha256": sha256(records_bytes).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
        }
        path = root / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def load(self, root: Path) -> tuple[dict, list[dict], list[dict], list[dict]]:
        manifest = json.loads((root / "manifest.json").read_text())
        payloads = {}
        for name in ("cases", "observations", "summary"):
            data = (root / f"{name}.json").read_bytes()
            if sha256(data).hexdigest() != manifest[f"{name}_sha256"]:
                raise ValueError(f"Scaling {name} hash mismatch")
            payloads[name] = json.loads(data)
        if len(payloads["cases"]) != manifest["case_count"] or len(payloads["observations"]) != manifest["observation_count"]:
            raise ValueError("Scaling evidence count mismatch")
        return manifest, payloads["cases"], payloads["observations"], payloads["summary"]


class ScalingRuntimeFingerprint:
    """Capture timing-critical runtime and scientific source identity."""

    THREAD_VARIABLES = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")
    SCIENTIFIC_SUFFIXES = (".py", ".yml", ".yaml", ".lock", ".txt")

    def capture(self) -> dict:
        commit = self._git(("rev-parse", "HEAD"))
        dirty_paths = tuple(filter(None, self._git(("status", "--porcelain")).splitlines()))
        normalized = tuple(line[3:] if len(line) > 3 else line for line in dirty_paths)
        scientific_dirty = tuple(
            path for path in normalized
            if path.endswith(self.SCIENTIFIC_SUFFIXES) or Path(path).name in {"Dockerfile", "Makefile"}
        )
        return {
            "git_commit": commit,
            "dirty_paths": list(normalized),
            "scientific_source_dirty": bool(scientific_dirty),
            "scientific_dirty_paths": list(scientific_dirty),
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "thread_settings": {name: os.environ.get(name) for name in self.THREAD_VARIABLES},
            "environment": EnvironmentSpecificationFingerprint().capture(("environment-ai.yml", "requirements-ai-pip.txt")),
        }

    @staticmethod
    def _git(arguments: tuple[str, ...]) -> str:
        completed = subprocess.run(("git", *arguments), check=True, capture_output=True, text=True)
        return completed.stdout.strip()
