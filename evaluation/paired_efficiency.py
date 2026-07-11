"""Paired, certificate-backed evaluation for learned branch ordering claims."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import median
from time import perf_counter

from benchmark.generator import BenchmarkInstance
from evaluation.policy import LearnedPolicyEvaluator
from synthesis.baselines import CertifiedSynthesisSolver
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import LearnedBranchOrderingPolicy


@dataclass(frozen=True)
class PairedEfficiencyOutcome:
    """One same-instance comparison; neither side can bypass certification."""

    instance_id: str
    baseline_valid: bool
    baseline_correct_classification: bool
    baseline_runtime_s: float
    policy_valid: bool
    policy_correct_classification: bool
    policy_runtime_s: float

    @property
    def policy_time_reduction(self) -> float:
        """Positive values mean that the policy was faster on this instance."""
        if self.baseline_runtime_s <= 0.0:
            raise ValueError("Baseline runtime must be positive")
        return (self.baseline_runtime_s - self.policy_runtime_s) / self.baseline_runtime_s


@dataclass(frozen=True)
class PairedEfficiencySummary:
    """Predeclared effect gate for retaining a learned-policy paper claim."""

    observations: int
    baseline_valid_rate: float
    policy_valid_rate: float
    median_policy_time_reduction: float
    bootstrap_low: float
    bootstrap_high: float
    preserves_modeled_validity: bool
    meets_learning_effect_gate: bool


class PairedEfficiencyStudy:
    """Evaluate one fixed policy against a deterministic certified baseline.

    The timing protocol performs a fixed number of independent evaluations per
    instance and uses the median for each method before paired bootstrap
    inference.  This prevents a single timing spike from becoming a paper
    result while retaining the original certificate for every outcome.
    """

    def __init__(
        self,
        baseline: CertifiedSynthesisSolver,
        max_actions: int,
        timing_repetitions: int = 3,
        bootstrap_samples: int = 1_000,
        bootstrap_seed: int = 2026,
        minimum_time_reduction: float = 0.30,
    ):
        if timing_repetitions < 1:
            raise ValueError("timing_repetitions must be positive")
        if bootstrap_samples < 10:
            raise ValueError("At least ten bootstrap samples are required")
        if not 0.0 <= minimum_time_reduction <= 1.0:
            raise ValueError("minimum_time_reduction must be within [0, 1]")
        self._baseline = baseline
        self._evaluator = LearnedPolicyEvaluator(max_actions)
        self._timing_repetitions = timing_repetitions
        self._bootstrap_samples = bootstrap_samples
        self._random = Random(bootstrap_seed)
        self._minimum_time_reduction = minimum_time_reduction

    def evaluate(
        self, policy: LearnedBranchOrderingPolicy, instances: list[BenchmarkInstance]
    ) -> list[PairedEfficiencyOutcome]:
        if not instances:
            raise ValueError("At least one benchmark instance is required")
        outcomes: list[PairedEfficiencyOutcome] = []
        for instance in instances:
            baseline_valid, baseline_correct, baseline_runtime = self._evaluate_baseline(instance)
            policy_outcome = self._evaluate_policy(policy, instance)
            outcomes.append(PairedEfficiencyOutcome(
                instance.instance_id,
                baseline_valid,
                baseline_correct,
                baseline_runtime,
                policy_outcome.valid,
                policy_outcome.correct_classification,
                policy_outcome.runtime_s,
            ))
        return outcomes

    def summarize(self, outcomes: list[PairedEfficiencyOutcome]) -> PairedEfficiencySummary:
        if not outcomes:
            raise ValueError("At least one paired outcome is required")
        reductions = [outcome.policy_time_reduction for outcome in outcomes]
        samples = sorted(
            median(self._random.choice(reductions) for _ in reductions)
            for _ in range(self._bootstrap_samples)
        )
        baseline_valid_rate = sum(item.baseline_valid for item in outcomes) / len(outcomes)
        policy_valid_rate = sum(item.policy_valid for item in outcomes) / len(outcomes)
        preserves_validity = policy_valid_rate == 1.0 and policy_valid_rate >= baseline_valid_rate
        lower = samples[int(self._bootstrap_samples * 0.025)]
        upper = samples[int(self._bootstrap_samples * 0.975) - 1]
        return PairedEfficiencySummary(
            len(outcomes),
            baseline_valid_rate,
            policy_valid_rate,
            median(reductions),
            lower,
            upper,
            preserves_validity,
            preserves_validity and lower > self._minimum_time_reduction,
        )

    def _evaluate_baseline(self, instance: BenchmarkInstance) -> tuple[bool, bool, float]:
        runtimes: list[float] = []
        valid = False
        for _ in range(self._timing_repetitions):
            graph = CertifiedSynthesisGraph(instance.problem, instance.reference_train.stages, instance.reference_train.meshes)
            started = perf_counter()
            result = self._baseline.solve(graph)
            runtimes.append(perf_counter() - started)
            valid = result is not None and bool(result.certificate_json["valid"])
        return valid, valid == instance.expected_feasible, median(runtimes)

    def _evaluate_policy(self, policy: LearnedBranchOrderingPolicy, instance: BenchmarkInstance):
        outcomes = []
        for _ in range(self._timing_repetitions):
            outcomes.append(self._evaluator.evaluate(policy, [instance])[0])
        representative = outcomes[-1]
        return type(representative)(
            representative.instance_id,
            representative.valid,
            representative.correct_classification,
            median(item.runtime_s for item in outcomes),
            representative.certificate_json,
        )
