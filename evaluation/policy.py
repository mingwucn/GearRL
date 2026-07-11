"""Evaluation of masked learned branch-ordering policies on certified graphs."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from benchmark.generator import BenchmarkInstance
from synthesis.certified_environment import CertifiedBranchOrderingEnvironment
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import LearnedBranchOrderingPolicy


@dataclass(frozen=True)
class PolicyOutcome:
    instance_id: str
    valid: bool
    correct_classification: bool
    runtime_s: float
    certificate_json: dict | None


class LearnedPolicyEvaluator:
    """Evaluate a policy through the same masked environment used for refinement."""

    def __init__(self, max_actions: int):
        self._max_actions = max_actions

    def evaluate(self, policy: LearnedBranchOrderingPolicy, instances: list[BenchmarkInstance]) -> list[PolicyOutcome]:
        outcomes: list[PolicyOutcome] = []
        for instance in instances:
            started = perf_counter()
            graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
            environment = CertifiedBranchOrderingEnvironment(graph, self._max_actions)
            state = environment.reset()
            while not state.terminal:
                try:
                    state = environment.step_policy(policy)
                except ValueError:
                    state = None
                    break
            certificate = state.certificate_json if state is not None else None
            valid = bool(certificate and certificate["valid"])
            outcomes.append(PolicyOutcome(instance.instance_id, valid, valid == instance.expected_feasible, perf_counter() - started, certificate))
        return outcomes
