"""Frozen 400-instance protocol for the certified planar benchmark."""

from __future__ import annotations

from dataclasses import dataclass, replace

from benchmark.generator import BenchmarkGenerator, BenchmarkInstance
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class BenchmarkProtocol:
    """Predeclared split sizes and seeds for the AEI digital benchmark."""

    seed: int = 2026
    train_procedural: int = 120
    validation_procedural: int = 60
    test_procedural: int = 70
    test_tight_clearance: int = 50
    test_near_infeasible: int = 100

    @property
    def instance_count(self) -> int:
        return self.train_procedural + self.validation_procedural + self.test_procedural + self.test_tight_clearance + self.test_near_infeasible

    def to_json(self) -> dict[str, int]:
        return {
            "seed": self.seed,
            "train_procedural": self.train_procedural,
            "validation_procedural": self.validation_procedural,
            "test_procedural": self.test_procedural,
            "test_tight_clearance": self.test_tight_clearance,
            "test_near_infeasible": self.test_near_infeasible,
            "instance_count": self.instance_count,
        }


class FrozenBenchmarkFactory:
    """Create every protocol partition with verifier-backed feasibility labels."""

    def __init__(self, generator: BenchmarkGenerator | None = None):
        self._generator = generator or BenchmarkGenerator()

    def generate(self, protocol: BenchmarkProtocol) -> list[BenchmarkInstance]:
        if protocol.instance_count != 400:
            raise ValueError("The publication protocol must contain exactly 400 instances")
        partitions = [
            self._procedural(protocol.seed + 101, protocol.train_procedural, "train"),
            self._procedural(protocol.seed + 202, protocol.validation_procedural, "validation"),
            self._procedural(protocol.seed + 303, protocol.test_procedural, "test"),
            self._tight(protocol.seed + 404, protocol.test_tight_clearance),
            self._near_infeasible(protocol.seed + 505, protocol.test_near_infeasible),
        ]
        instances = [item for partition in partitions for item in partition]
        if len({item.instance_id for item in instances}) != len(instances):
            raise RuntimeError("Protocol instance identifiers must be unique")
        return instances

    def _procedural(self, seed: int, count: int, partition: str) -> list[BenchmarkInstance]:
        return [
            replace(item, instance_id=f"{partition}-procedural-{index:04d}", partition=partition, difficulty=("easy", "moderate", "hard")[index % 3])
            for index, item in enumerate(self._generator.generate_compound_instances(seed, count))
        ]

    def _tight(self, seed: int, count: int) -> list[BenchmarkInstance]:
        result = []
        for index, item in enumerate(self._generator.generate_compound_instances(seed, count)):
            clearance = max(0.0, float(item.certificate["minimum_clearance_mm"]) - 0.01)
            problem = replace(item.problem, constraints=replace(item.problem.constraints, boundary_clearance=clearance))
            certificate = ReferenceVerifier.verify(problem, item.reference_train)
            if not certificate.valid:
                raise RuntimeError("Tight-clearance construction must remain feasible")
            result.append(replace(item, instance_id=f"test-tight-clearance-{index:04d}", problem=problem, certificate=certificate.to_json(), partition="test", difficulty="hard", family="adversarial-tight-clearance"))
        return result

    def _near_infeasible(self, seed: int, count: int) -> list[BenchmarkInstance]:
        result = []
        for index, item in enumerate(self._generator.generate_compound_instances(seed, count)):
            clearance = float(item.certificate["minimum_clearance_mm"]) + 0.01
            problem = replace(item.problem, constraints=replace(item.problem.constraints, boundary_clearance=clearance))
            certificate = ReferenceVerifier.verify(problem, item.reference_train)
            if certificate.valid:
                raise RuntimeError("Near-infeasible construction must be infeasible")
            result.append(replace(item, instance_id=f"test-near-infeasible-{index:04d}", problem=problem, certificate=certificate.to_json(), expected_feasible=False, partition="test", difficulty="hard", family="adversarial-near-infeasible"))
        return result
