"""Independent SciPy baseline for the published planetary-gear brief."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

from benchmark.planetary_external import (
    PlanetaryGearCandidate,
    PlanetaryGearEvaluation,
    PublishedPlanetaryGearBrief,
    PublishedPlanetaryGearEvaluator,
)


@dataclass(frozen=True)
class PlanetaryBaselineProtocol:
    study_id: str
    seeds: tuple[int, ...]
    population_multiplier: int
    maximum_iterations: int
    objective_acceptance_threshold: float

    def to_json(self) -> dict:
        return {
            "study_id": self.study_id,
            "seeds": list(self.seeds),
            "population_multiplier": self.population_multiplier,
            "maximum_iterations": self.maximum_iterations,
            "objective_acceptance_threshold": self.objective_acceptance_threshold,
        }


class PlanetaryBaselineProtocolLoader:
    def load(self, path: Path) -> PlanetaryBaselineProtocol:
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != "planetary-baseline-protocol-v1":
            raise ValueError("Unsupported planetary baseline protocol")
        return PlanetaryBaselineProtocol(
            payload["study_id"],
            tuple(map(int, payload["seeds"])),
            int(payload["population_multiplier"]),
            int(payload["maximum_iterations"]),
            float(payload["objective_acceptance_threshold"]),
        )


class PlanetaryDecisionDecoder:
    """Decode nine integral optimizer coordinates into published discrete choices."""

    def decode(self, brief: PublishedPlanetaryGearBrief, vector: np.ndarray) -> PlanetaryGearCandidate:
        teeth = tuple(int(round(value)) for value in vector[:6])
        planet_index = int(np.clip(round(vector[6]), 0, len(brief.planet_choices) - 1))
        module_1_index = int(np.clip(round(vector[7]), 0, len(brief.module_choices_mm) - 1))
        module_2_index = int(np.clip(round(vector[8]), 0, len(brief.module_choices_mm) - 1))
        return PlanetaryGearCandidate(
            *teeth,
            brief.planet_choices[planet_index],
            brief.module_choices_mm[module_1_index],
            brief.module_choices_mm[module_2_index],
        )


class PlanetaryPenaltyObjective:
    """Feasibility-first normalized penalty around the source objective."""

    def calculate(self, evaluation: PlanetaryGearEvaluation) -> float:
        if not np.isfinite(evaluation.objective) or not evaluation.inequality_values:
            return 1e12
        scales = (220.0, 220.0, 220.0, 10.0, 100.0, 100.0, 10000.0, 100.0, 100.0, 100.0)
        violation = sum((max(0.0, value) / scale) ** 2 for value, scale in zip(evaluation.inequality_values, scales, strict=True))
        violation += float(evaluation.assembly_remainder != 0)
        return evaluation.objective + 1e6 * violation


@dataclass(frozen=True)
class PlanetaryBaselineResult:
    seed: int
    candidate: PlanetaryGearCandidate
    evaluation: PlanetaryGearEvaluation
    objective_calls: int
    optimizer_success: bool
    optimizer_message: str

    def to_json(self) -> dict:
        return {
            "seed": self.seed,
            "candidate": self.candidate.to_json(),
            "evaluation": self.evaluation.to_json(),
            "objective_calls": self.objective_calls,
            "optimizer_success": self.optimizer_success,
            "optimizer_message": self.optimizer_message,
        }

    @classmethod
    def from_json(cls, payload: dict) -> "PlanetaryBaselineResult":
        return cls(
            seed=int(payload["seed"]),
            candidate=PlanetaryGearCandidate.from_json(payload["candidate"]),
            evaluation=PlanetaryGearEvaluation.from_json(payload["evaluation"]),
            objective_calls=int(payload["objective_calls"]),
            optimizer_success=bool(payload["optimizer_success"]),
            optimizer_message=str(payload["optimizer_message"]),
        )


class PlanetaryDifferentialEvolutionBaseline:
    def __init__(self) -> None:
        self._decoder = PlanetaryDecisionDecoder()
        self._evaluator = PublishedPlanetaryGearEvaluator()
        self._penalty = PlanetaryPenaltyObjective()

    def solve(self, brief: PublishedPlanetaryGearBrief, protocol: PlanetaryBaselineProtocol, seed: int) -> PlanetaryBaselineResult:
        bounds = tuple((item.minimum, item.maximum) for item in brief.tooth_ranges) + (
            (0, len(brief.planet_choices) - 1),
            (0, len(brief.module_choices_mm) - 1),
            (0, len(brief.module_choices_mm) - 1),
        )
        calls = 0

        def objective(vector: np.ndarray) -> float:
            nonlocal calls
            calls += 1
            candidate = self._decoder.decode(brief, vector)
            return self._penalty.calculate(self._evaluator.evaluate(brief, candidate))

        result = differential_evolution(
            objective,
            bounds,
            seed=seed,
            popsize=protocol.population_multiplier,
            maxiter=protocol.maximum_iterations,
            integrality=np.ones(9, dtype=bool),
            polish=False,
            workers=1,
            updating="immediate",
            tol=0.0,
            atol=0.0,
        )
        candidate = self._decoder.decode(brief, result.x)
        evaluation = self._evaluator.evaluate(brief, candidate)
        return PlanetaryBaselineResult(seed, candidate, evaluation, calls, bool(result.success), str(result.message))


class PlanetaryBaselineEvidenceStore:
    @staticmethod
    def _encode(payload: dict) -> bytes:
        return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()

    def write(self, protocol: PlanetaryBaselineProtocol, results: tuple[PlanetaryBaselineResult, ...], protocol_source: Path, destination: Path) -> Path:
        if destination.exists() and any(destination.iterdir()):
            raise FileExistsError("Planetary baseline destination must be empty")
        destination.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "planetary-baseline-summary-v1",
            "study_id": protocol.study_id,
            "protocol": protocol.to_json(),
            "source_case": PublishedPlanetaryGearBrief().to_json(),
            "results": [result.to_json() for result in results],
            "valid_run_count": sum(result.evaluation.valid for result in results),
            "threshold_run_count": sum(result.evaluation.valid and result.evaluation.objective <= protocol.objective_acceptance_threshold for result in results),
            "best_valid_objective": min((result.evaluation.objective for result in results if result.evaluation.valid), default=None),
            "conversion_status": "pending-independent-review",
        }
        summary_bytes = self._encode(payload)
        (destination / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "schema_version": "planetary-baseline-artifact-v1",
            "protocol_source": str(protocol_source),
            "protocol_sha256": sha256(protocol_source.read_bytes()).hexdigest(),
            "summary_sha256": sha256(summary_bytes).hexdigest(),
        }
        path = destination / "manifest.json"
        path.write_bytes(self._encode(manifest))
        return path

    def verify(self, destination: Path) -> dict:
        manifest = json.loads((destination / "manifest.json").read_text())
        if sha256((destination / "summary.json").read_bytes()).hexdigest() != manifest["summary_sha256"]:
            raise ValueError("Planetary baseline summary hash mismatch")
        source = Path(manifest["protocol_source"])
        if sha256(source.read_bytes()).hexdigest() != manifest["protocol_sha256"]:
            raise ValueError("Planetary baseline protocol hash mismatch")
        return manifest


class PlanetaryBaselineBatchMerger:
    """Combine independently computed batches only after complete verification."""

    def __init__(self, evidence_store: PlanetaryBaselineEvidenceStore | None = None) -> None:
        self._evidence_store = evidence_store or PlanetaryBaselineEvidenceStore()

    def merge(
        self,
        protocol: PlanetaryBaselineProtocol,
        batch_directories: tuple[Path, ...],
        protocol_source: Path,
        destination: Path,
    ) -> Path:
        results: dict[int, PlanetaryBaselineResult] = {}
        expected_protocol = protocol.to_json()
        expected_case = json.loads(json.dumps(PublishedPlanetaryGearBrief().to_json()))
        for directory in batch_directories:
            self._evidence_store.verify(directory)
            payload = json.loads((directory / "summary.json").read_text())
            if payload.get("schema_version") != "planetary-baseline-summary-v1":
                raise ValueError("Unsupported planetary batch summary")
            if payload.get("study_id") != protocol.study_id or payload.get("protocol") != expected_protocol:
                raise ValueError("Planetary batch protocol mismatch")
            if payload.get("source_case") != expected_case:
                raise ValueError("Planetary batch source case mismatch")
            if payload.get("conversion_status") != "pending-independent-review":
                raise ValueError("Planetary batch conversion status is not pending review")
            for result_payload in payload["results"]:
                result = PlanetaryBaselineResult.from_json(result_payload)
                if result.seed in results:
                    raise ValueError(f"Duplicate planetary baseline seed: {result.seed}")
                results[result.seed] = result

        expected_seeds = set(protocol.seeds)
        actual_seeds = set(results)
        if actual_seeds != expected_seeds:
            missing = sorted(expected_seeds - actual_seeds)
            unexpected = sorted(actual_seeds - expected_seeds)
            raise ValueError(f"Planetary batch seed coverage mismatch; missing={missing}, unexpected={unexpected}")
        ordered = tuple(results[seed] for seed in protocol.seeds)
        return self._evidence_store.write(protocol, ordered, protocol_source, destination)
