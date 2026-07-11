"""Joint digital robustness study for assembly-location uncertainty."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal
import gzip
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from benchmark.loader import FrozenBenchmarkLoader
from common.design_models import GearStage, GearTrain, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class AssemblyRobustnessProtocol:
    sample_size: int = 120
    draws_per_layout: int = 512
    bootstrap_samples: int = 5000
    random_seed: int = 2026
    shaft_location_tolerances_mm: tuple[float, ...] = (0.005, 0.01, 0.025)
    housing_clearance_erosions_mm: tuple[float, ...] = (0.0, 0.05, 0.1)
    transverse_backlash_allowances_mm: tuple[float, ...] = (0.0, 0.02, 0.05)

    def __post_init__(self) -> None:
        if min(self.sample_size, self.draws_per_layout, self.bootstrap_samples) < 1:
            raise ValueError("Robustness sample counts must be positive")
        if any(value < 0 for values in (self.shaft_location_tolerances_mm, self.housing_clearance_erosions_mm, self.transverse_backlash_allowances_mm) for value in values):
            raise ValueError("Robustness tolerances must be non-negative")


class AssemblyRobustnessProtocolLoader:
    """Load a versioned protocol without allowing undeclared runtime overrides."""

    def load(self, path: Path) -> AssemblyRobustnessProtocol:
        payload = json.loads(path.read_text())
        if payload["schema_version"] != "assembly-robustness-protocol-v1":
            raise ValueError("Unsupported assembly robustness protocol schema")
        config = payload["config"]
        return AssemblyRobustnessProtocol(
            sample_size=int(config["sample_size"]),
            draws_per_layout=int(config["draws_per_layout"]),
            bootstrap_samples=int(config["bootstrap_samples"]),
            random_seed=int(config["random_seed"]),
            shaft_location_tolerances_mm=tuple(map(float, config["shaft_location_tolerances_mm"])),
            housing_clearance_erosions_mm=tuple(map(float, config["housing_clearance_erosions_mm"])),
            transverse_backlash_allowances_mm=tuple(map(float, config["transverse_backlash_allowances_mm"])),
        )


@dataclass(frozen=True)
class AssemblyScenario:
    scenario_id: str
    shaft_location_tolerance_mm: float
    housing_clearance_erosion_mm: float
    transverse_backlash_allowance_mm: float


@dataclass(frozen=True)
class AssemblyDrawOutcome:
    layout_id: str
    scenario_id: str
    draw_index: int
    valid: bool
    failure_codes: tuple[str, ...]


class AssemblyScenarioIdentity:
    """Create readable, injective identities from protocol decimal values."""

    @staticmethod
    def _decimal(value: float) -> str:
        return format(Decimal(str(value)).normalize(), "f")

    def create(self, shaft: float, housing: float, backlash: float) -> str:
        return "--".join((
            f"shaft-{self._decimal(shaft)}",
            f"housing-{self._decimal(housing)}",
            f"backlash-{self._decimal(backlash)}",
        ))


class AssemblyScenarioFactory:
    def __init__(self) -> None:
        self._identity = AssemblyScenarioIdentity()

    def create(self, protocol: AssemblyRobustnessProtocol) -> tuple[AssemblyScenario, ...]:
        scenarios = []
        for shaft in protocol.shaft_location_tolerances_mm:
            for housing in protocol.housing_clearance_erosions_mm:
                for backlash in protocol.transverse_backlash_allowances_mm:
                    identifier = self._identity.create(shaft, housing, backlash)
                    scenarios.append(AssemblyScenario(identifier, shaft, housing, backlash))
        result = tuple(scenarios)
        identifiers = tuple(scenario.scenario_id for scenario in result)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Assembly robustness scenario identifiers must be unique")
        return result


class AssemblyPerturbationSampler:
    """Generate repeatable independent shaft-center errors with input fixed."""

    def sample(self, seed: int, draws: int, movable_stage_count: int) -> np.ndarray:
        return np.random.default_rng(seed).uniform(-1.0, 1.0, size=(draws, movable_stage_count, 2))


class AssemblyRobustnessEvaluator:
    def evaluate(self, problem, train: GearTrain, scenario: AssemblyScenario, normalized_errors: np.ndarray) -> Iterable[AssemblyDrawOutcome]:
        constraints = replace(
            problem.constraints,
            boundary_clearance=problem.constraints.boundary_clearance + scenario.housing_clearance_erosion_mm,
            transverse_backlash_allowance_mm=scenario.transverse_backlash_allowance_mm,
        )
        declared_problem = replace(problem, constraints=constraints)
        input_id = problem.input_stage_id
        movable = [stage for stage in train.stages if stage.id != input_id]
        if normalized_errors.shape[1:] != (len(movable), 2):
            raise ValueError("Perturbation tensor does not match movable shafts")
        for draw_index, errors in enumerate(normalized_errors):
            error_by_id = {stage.id: errors[index] * scenario.shaft_location_tolerance_mm for index, stage in enumerate(movable)}
            stages: list[GearStage] = []
            for stage in train.stages:
                if stage.id == input_id:
                    stages.append(stage)
                else:
                    delta = error_by_id[stage.id]
                    stages.append(replace(stage, center=Point2D(stage.center.x + float(delta[0]), stage.center.y + float(delta[1]))))
            certificate = ReferenceVerifier.verify(declared_problem, GearTrain(tuple(stages), train.meshes))
            yield AssemblyDrawOutcome("", scenario.scenario_id, draw_index, certificate.valid, tuple(sorted({issue.code for issue in certificate.issues})))


class LayoutBootstrapInterval:
    def calculate(self, probabilities: np.ndarray, samples: int, seed: int) -> tuple[float, float]:
        generator = np.random.default_rng(seed)
        means = np.empty(samples)
        for index in range(samples):
            means[index] = probabilities[generator.integers(0, len(probabilities), len(probabilities))].mean()
        low, high = np.quantile(means, (0.025, 0.975))
        return float(low), float(high)


class AssemblyRobustnessStudy:
    """Run all layouts against a shared, preregistered perturbation design."""

    def __init__(self) -> None:
        self._scenarios = AssemblyScenarioFactory()
        self._sampler = AssemblyPerturbationSampler()
        self._evaluator = AssemblyRobustnessEvaluator()
        self._bootstrap = LayoutBootstrapInterval()

    def run(self, dataset: Path, protocol: AssemblyRobustnessProtocol) -> tuple[dict, list[AssemblyDrawOutcome], str, str]:
        dataset_id, dataset_hash, instances = FrozenBenchmarkLoader().load(dataset)
        selected = [instance for instance in instances if instance.expected_feasible][: protocol.sample_size]
        if len(selected) != protocol.sample_size:
            raise ValueError("Dataset does not contain the declared number of feasible layouts")
        scenarios = self._scenarios.create(protocol)
        outcomes: list[AssemblyDrawOutcome] = []
        layout_rates = {scenario.scenario_id: [] for scenario in scenarios}
        failure_counts = {scenario.scenario_id: {} for scenario in scenarios}
        for layout_index, instance in enumerate(selected):
            movable_count = sum(stage.id != instance.problem.input_stage_id for stage in instance.reference_train.stages)
            errors = self._sampler.sample(protocol.random_seed + layout_index, protocol.draws_per_layout, movable_count)
            for scenario in scenarios:
                valid_count = 0
                for outcome in self._evaluator.evaluate(instance.problem, instance.reference_train, scenario, errors):
                    bound = replace(outcome, layout_id=instance.instance_id)
                    outcomes.append(bound)
                    valid_count += int(bound.valid)
                    for code in bound.failure_codes:
                        failure_counts[scenario.scenario_id][code] = failure_counts[scenario.scenario_id].get(code, 0) + 1
                layout_rates[scenario.scenario_id].append(valid_count / protocol.draws_per_layout)
        summaries = []
        for scenario_index, scenario in enumerate(scenarios):
            probabilities = np.asarray(layout_rates[scenario.scenario_id])
            interval = self._bootstrap.calculate(probabilities, protocol.bootstrap_samples, protocol.random_seed + 10000 + scenario_index)
            summaries.append({
                **asdict(scenario),
                "modeled_valid_probability": float(probabilities.mean()),
                "layout_bootstrap_95_interval": list(interval),
                "minimum_layout_probability": float(probabilities.min()),
                "maximum_layout_probability": float(probabilities.max()),
                "failure_code_counts": failure_counts[scenario.scenario_id],
            })
        summary = {
            "schema_version": "assembly-robustness-summary-v1",
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "protocol": asdict(protocol),
            "layout_count": len(selected),
            "scenario_count": len(scenarios),
            "draw_count": len(outcomes),
            "scope": "conditional digital assembly robustness under declared uniform shaft-location errors, conservative housing-clearance erosion, and transverse-backlash allowance",
            "scenarios": summaries,
        }
        return summary, outcomes, dataset_id, dataset_hash


class AssemblyRobustnessEvidenceStore:
    """Persist deterministic compressed draw-level evidence and verify hashes."""

    @staticmethod
    def _json_bytes(payload) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, summary: dict, outcomes: list[AssemblyDrawOutcome], source_index: Path, destination: Path, protocol_source: Path | None = None) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Assembly robustness destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        summary_bytes = self._json_bytes(summary)
        (destination / "summary.json").write_bytes(summary_bytes)
        raw_path = destination / "draws.jsonl.gz"
        with raw_path.open("wb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
                for outcome in outcomes:
                    compressed.write(json.dumps(asdict(outcome), sort_keys=True, separators=(",", ":")).encode() + b"\n")
        manifest = {
            "schema_version": "assembly-robustness-artifact-v2",
            "model_version": "certified-planar-v3+assembly-robustness-v2",
            "source_index": str(source_index),
            "source_index_sha256": sha256(source_index.read_bytes()).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
            "draws_sha256": sha256(raw_path.read_bytes()).hexdigest(),
            "draw_count": len(outcomes),
        }
        if protocol_source is not None:
            manifest["protocol_source"] = str(protocol_source)
            manifest["protocol_source_sha256"] = sha256(protocol_source.read_bytes()).hexdigest()
        path = destination / "manifest.json"
        path.write_bytes(self._json_bytes(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        checks = {
            "source_index_sha256": Path(manifest["source_index"]).read_bytes(),
            "summary_sha256": (destination / "summary.json").read_bytes(),
            "draws_sha256": (destination / "draws.jsonl.gz").read_bytes(),
        }
        if "protocol_source" in manifest:
            checks["protocol_source_sha256"] = Path(manifest["protocol_source"]).read_bytes()
        for field, content in checks.items():
            if sha256(content).hexdigest() != manifest[field]:
                raise ValueError(f"Assembly robustness {field} mismatch")
        with gzip.open(destination / "draws.jsonl.gz", "rt") as source:
            count = sum(1 for _ in source)
        if count != manifest["draw_count"]:
            raise ValueError("Assembly robustness draw count mismatch")
        AssemblyRobustnessSemanticVerifier().verify(destination)
        return manifest


class AssemblyRobustnessSemanticVerifier:
    """Independently reconstruct summary evidence from ordered raw outcomes."""

    def __init__(self) -> None:
        self._bootstrap = LayoutBootstrapInterval()

    @staticmethod
    def _scenario_map(summary: dict) -> dict[str, dict]:
        scenarios = summary.get("scenarios", [])
        identifiers = [scenario["scenario_id"] for scenario in scenarios]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Assembly robustness scenario identifiers are not unique")
        if len(scenarios) != summary.get("scenario_count"):
            raise ValueError("Assembly robustness scenario cardinality mismatch")
        return dict(zip(identifiers, scenarios, strict=True))

    def verify(self, destination: Path) -> None:
        summary = json.loads((destination / "summary.json").read_text())
        scenarios = self._scenario_map(summary)
        protocol = summary["protocol"]
        layout_count = int(summary["layout_count"])
        draws_per_layout = int(protocol["draws_per_layout"])
        expected_scenarios = tuple(scenarios)
        rates = {identifier: [] for identifier in expected_scenarios}
        failures = {identifier: {} for identifier in expected_scenarios}
        layout_ids: list[str] = []
        line_count = 0

        with gzip.open(destination / "draws.jsonl.gz", "rt") as source:
            for layout_index in range(layout_count):
                layout_id = None
                for scenario_id in expected_scenarios:
                    valid_count = 0
                    for draw_index in range(draws_per_layout):
                        line = source.readline()
                        if not line:
                            raise ValueError("Assembly robustness raw evidence ended early")
                        line_count += 1
                        outcome = json.loads(line)
                        if layout_id is None:
                            layout_id = outcome["layout_id"]
                        if outcome["layout_id"] != layout_id:
                            raise ValueError("Assembly robustness layout ordering mismatch")
                        if outcome["scenario_id"] != scenario_id or outcome["draw_index"] != draw_index:
                            raise ValueError("Assembly robustness scenario/draw ordering mismatch")
                        valid_count += int(outcome["valid"])
                        for code in set(outcome["failure_codes"]):
                            failures[scenario_id][code] = failures[scenario_id].get(code, 0) + 1
                    rates[scenario_id].append(valid_count / draws_per_layout)
                if layout_id in layout_ids:
                    raise ValueError("Assembly robustness layout identifiers are not unique")
                layout_ids.append(layout_id)
            if source.readline():
                raise ValueError("Assembly robustness raw evidence has undeclared extra draws")

        expected_count = layout_count * len(expected_scenarios) * draws_per_layout
        if line_count != expected_count or summary.get("draw_count") != expected_count:
            raise ValueError("Assembly robustness semantic draw count mismatch")
        for scenario_index, scenario_id in enumerate(expected_scenarios):
            recorded = scenarios[scenario_id]
            probabilities = np.asarray(rates[scenario_id])
            interval = self._bootstrap.calculate(
                probabilities,
                int(protocol["bootstrap_samples"]),
                int(protocol["random_seed"]) + 10000 + scenario_index,
            )
            reconstructed = {
                "modeled_valid_probability": float(probabilities.mean()),
                "layout_bootstrap_95_interval": list(interval),
                "minimum_layout_probability": float(probabilities.min()),
                "maximum_layout_probability": float(probabilities.max()),
                "failure_code_counts": failures[scenario_id],
            }
            for field, value in reconstructed.items():
                if recorded.get(field) != value:
                    raise ValueError(f"Assembly robustness semantic {field} mismatch for {scenario_id}")
