"""Seeded, self-certifying benchmark instances for planar compound trains."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from random import Random
from typing import Any

from common.design_models import DesignConstraints, DesignProblem, GearStage, GearTrain, MeshEdge, Point2D
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class BenchmarkInstance:
    instance_id: str
    seed: int
    problem: DesignProblem
    reference_train: GearTrain
    certificate: dict[str, Any]
    expected_feasible: bool = True
    family: str = "compound-straight"

    def to_json(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "seed": self.seed,
            "problem": asdict(self.problem),
            "reference_train": self.reference_train.to_json(),
            "certificate": self.certificate,
            "expected_feasible": self.expected_feasible,
            "family": self.family,
        }


class BenchmarkGenerator:
    """Seeded benchmark factory with one canonical generation policy."""

    def __init__(self, min_teeth: int = 18, max_teeth: int = 48):
        if min_teeth < 3 or max_teeth < min_teeth:
            raise ValueError("Invalid benchmark tooth-count bounds")
        self._min_teeth = min_teeth
        self._max_teeth = max_teeth

    def generate_compound_instances(self, seed: int, count: int) -> list[BenchmarkInstance]:
        return _generate_compound_instances(seed, count, self._min_teeth, self._max_teeth)

    def generate_suite(self, seed: int, feasible_count: int, infeasible_count: int) -> list[BenchmarkInstance]:
        if infeasible_count < 0:
            raise ValueError("infeasible_count must be non-negative")
        valid = self.generate_compound_instances(seed, feasible_count)
        invalid: list[BenchmarkInstance] = []
        for index, source in enumerate(self.generate_compound_instances(seed + 1, infeasible_count)):
            maximum_radius = max(stage.outer_radius_mm() for stage in source.reference_train.stages)
            enclosure_half_extent = max(abs(point.x) for point in source.problem.boundary)
            problem = replace(
                source.problem,
                constraints=replace(
                    source.problem.constraints,
                    boundary_clearance=enclosure_half_extent + maximum_radius + 1.0,
                ),
            )
            certificate = ReferenceVerifier.verify(problem, source.reference_train)
            if certificate.valid:
                raise RuntimeError("Adversarial benchmark construction must be infeasible")
            invalid.append(BenchmarkInstance(
                instance_id=f"infeasible-{seed}-{index:04d}",
                seed=seed,
                problem=problem,
                reference_train=source.reference_train,
                certificate=certificate.to_json(),
                expected_feasible=False,
                family="clearance-infeasible",
            ))
        if not valid and not invalid:
            raise ValueError("Benchmark suite must contain at least one instance")
        return [*valid, *invalid]


def _generate_compound_instances(seed: int, count: int, min_teeth: int, max_teeth: int) -> list[BenchmarkInstance]:
    """Generate reproducible two-mesh compound layouts with exact certificates.

    This is the first benchmark family.  Later families can share the JSON
    contract while adding obstacles, alternate enclosure geometry, and known
    infeasible cases.
    """

    if count < 0 or min_teeth < 3 or max_teeth < min_teeth:
        raise ValueError("Invalid benchmark generation bounds")
    rng = Random(seed)
    instances: list[BenchmarkInstance] = []
    for index in range(count):
        input_teeth, first_compound, second_compound, output_teeth = (
            rng.randint(min_teeth, max_teeth) for _ in range(4)
        )
        module_mm = rng.choice((1.0, 1.25, 1.5, 2.0))
        input_center = Point2D(0.0, 0.0)
        compound_center = Point2D(module_mm * (input_teeth + first_compound) / 2.0, 0.0)
        output_center = Point2D(
            compound_center.x + module_mm * (second_compound + output_teeth) / 2.0,
            0.0,
        )
        stages = (
            GearStage("input", input_center, (input_teeth,), module_mm, (0,)),
            GearStage("compound", compound_center, (first_compound, second_compound), module_mm, (0, 1)),
            GearStage("output", output_center, (output_teeth,), module_mm, (1,)),
        )
        meshes = (
            MeshEdge("input", 0, "compound", 0),
            MeshEdge("compound", 1, "output", 0),
        )
        train = GearTrain(stages, meshes)
        extent = output_center.x + max(stage.outer_radius_mm() for stage in stages) + 20.0
        family = ("compound-square", "compound-wide", "compound-tall", "compound-chamfered")[index % 4]
        problem = DesignProblem(
            boundary=_boundary_for_family(family, extent),
            input_stage_id="input",
            output_stage_id="output",
            constraints=DesignConstraints(
                target_speed_ratio=(input_teeth / first_compound) * (second_compound / output_teeth),
                min_teeth=min_teeth,
                max_teeth=max_teeth,
            ),
        )
        certificate = ReferenceVerifier.verify(problem, train)
        if not certificate.valid:
            raise RuntimeError(f"Benchmark generator emitted invalid instance {index}: {certificate.issues}")
        instances.append(BenchmarkInstance(
            f"compound-{seed}-{index:04d}", seed, problem, train, certificate.to_json(), family=family
        ))
    return instances


def _boundary_for_family(family: str, extent: float) -> tuple[Point2D, ...]:
    if family == "compound-square":
        return (Point2D(-extent, -extent), Point2D(extent, -extent), Point2D(extent, extent), Point2D(-extent, extent))
    if family == "compound-wide":
        return (Point2D(-extent * 1.5, -extent * 0.8), Point2D(extent * 1.5, -extent * 0.8), Point2D(extent * 1.5, extent * 0.8), Point2D(-extent * 1.5, extent * 0.8))
    if family == "compound-tall":
        return (Point2D(-extent, -extent * 1.5), Point2D(extent, -extent * 1.5), Point2D(extent, extent * 1.5), Point2D(-extent, extent * 1.5))
    if family == "compound-chamfered":
        edge = extent * 0.7
        return (
            Point2D(-edge, -extent), Point2D(edge, -extent), Point2D(extent, -edge), Point2D(extent, edge),
            Point2D(edge, extent), Point2D(-edge, extent), Point2D(-extent, edge), Point2D(-extent, -edge),
        )
    raise ValueError(f"Unknown benchmark family {family}")
