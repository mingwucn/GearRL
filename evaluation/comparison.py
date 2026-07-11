"""Equal-budget comparison of object-oriented certified solver strategies."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from benchmark.generator import BenchmarkInstance
from synthesis.baselines import CertifiedSynthesisSolver
from synthesis.certified_graph import CertifiedSynthesisGraph


@dataclass(frozen=True)
class SolverOutcome:
    instance_id: str
    solver_name: str
    valid: bool
    correct_classification: bool
    runtime_s: float
    score: tuple[int, float] | None


class CertifiedSolverComparison:
    """Run predeclared solvers without allowing them to bypass certification."""

    def evaluate(self, instances: list[BenchmarkInstance], solvers: dict[str, CertifiedSynthesisSolver]) -> list[SolverOutcome]:
        if not instances or not solvers:
            raise ValueError("At least one instance and one solver are required")
        outcomes: list[SolverOutcome] = []
        for instance in instances:
            graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
            for name, solver in solvers.items():
                started = perf_counter()
                result = solver.solve(graph)
                runtime = perf_counter() - started
                valid = result is not None and bool(result.certificate_json["valid"])
                outcomes.append(SolverOutcome(instance.instance_id, name, valid, valid == instance.expected_feasible, runtime, result.score if result else None))
        return outcomes
