"""Deterministic search over independently verified gear-mesh candidates."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from random import Random

from common.design_models import DesignProblem, GearStage, GearTrain, MeshEdge
from physics_validator.reference_verifier import ReferenceVerifier


@dataclass(frozen=True)
class SynthesisResult:
    train: GearTrain
    score: tuple[int, float]
    certificate_json: dict


class CertifiedSynthesisGraph:
    """Enumerate bounded mesh paths and retain only certified designs.

    Candidate geometry is supplied by a placement generator or benchmark.  The
    graph owns the topology decision and never returns a layout that fails the
    independent verifier.
    """

    def __init__(self, problem: DesignProblem, stages: tuple[GearStage, ...], meshes: tuple[MeshEdge, ...]):
        self.problem = problem
        self._stages = {stage.id: stage for stage in stages}
        self._meshes = meshes
        if problem.input_stage_id not in self._stages or problem.output_stage_id not in self._stages:
            raise ValueError("Candidates must include input and output stages")
        self._outgoing: dict[str, list[MeshEdge]] = {stage_id: [] for stage_id in self._stages}
        for edge in meshes:
            if edge.driver_stage_id in self._outgoing:
                self._outgoing[edge.driver_stage_id].append(edge)

    def solve(self, max_stages: int = 6) -> SynthesisResult | None:
        """Return the minimum-stage, minimum-area certified directed path."""
        if max_stages < 2:
            raise ValueError("max_stages must include input and output")
        results: list[SynthesisResult] = []
        self._search(self.problem.input_stage_id, [], {self.problem.input_stage_id}, max_stages, results)
        return min(results, key=lambda result: result.score) if results else None

    @property
    def stages(self) -> tuple[GearStage, ...]:
        return tuple(self._stages.values())

    def stage(self, stage_id: str) -> GearStage:
        return self._stages[stage_id]

    def candidates(self, stage_id: str, visited: set[str]) -> tuple[MeshEdge, ...]:
        return tuple(edge for edge in self._outgoing.get(stage_id, []) if edge.driven_stage_id not in visited)

    def certify_path(self, path: list[MeshEdge]) -> dict:
        """Return an independent certificate for one complete directed path."""
        train = self._train_from_path(path)
        return ReferenceVerifier.verify_with_cae(self.problem, train).to_json()

    def solve_greedy(self, max_stages: int = 6) -> SynthesisResult | None:
        """Follow the first available branch and certify only its terminal train."""
        return self._solve_ordered(max_stages, lambda edges: edges)

    def solve_random(self, random: Random, max_stages: int = 6) -> SynthesisResult | None:
        """Follow a seeded random candidate order without relaxing certification."""
        return self._solve_ordered(max_stages, lambda edges: random.sample(edges, len(edges)))

    def _solve_ordered(self, max_stages: int, order) -> SynthesisResult | None:
        current = self.problem.input_stage_id
        path: list[MeshEdge] = []
        visited = {current}
        while current != self.problem.output_stage_id and len(visited) < max_stages:
            available = [edge for edge in self._outgoing.get(current, []) if edge.driven_stage_id not in visited]
            if not available:
                return None
            edge = order(available)[0]
            path.append(edge)
            current = edge.driven_stage_id
            visited.add(current)
        if current != self.problem.output_stage_id:
            return None
        train = self._train_from_path(path)
        certificate = ReferenceVerifier.verify_with_cae(self.problem, train)
        return SynthesisResult(train, self._score(train), certificate.to_json()) if certificate.valid else None

    def _search(
        self,
        current: str,
        path: list[MeshEdge],
        visited: set[str],
        max_stages: int,
        results: list[SynthesisResult],
    ) -> None:
        if current == self.problem.output_stage_id:
            train = self._train_from_path(path)
            certificate = ReferenceVerifier.verify_with_cae(self.problem, train)
            if certificate.valid:
                results.append(SynthesisResult(train, self._score(train), certificate.to_json()))
            return
        if len(visited) >= max_stages:
            return
        for edge in self._outgoing.get(current, []):
            if edge.driven_stage_id in visited:
                continue
            self._search(
                edge.driven_stage_id,
                [*path, edge],
                visited | {edge.driven_stage_id},
                max_stages,
                results,
            )

    def _train_from_path(self, path: list[MeshEdge]) -> GearTrain:
        stage_ids = [self.problem.input_stage_id]
        for edge in path:
            stage_ids.append(edge.driven_stage_id)
        return GearTrain(tuple(self._stages[stage_id] for stage_id in stage_ids), tuple(path))

    @staticmethod
    def _score(train: GearTrain) -> tuple[int, float]:
        area = sum(pi * stage.outer_radius_mm() ** 2 for stage in train.stages)
        return len(train.stages), area
