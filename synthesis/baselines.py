"""Object-oriented deterministic baselines for certified graph synthesis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from random import Random

from synthesis.certified_graph import CertifiedSynthesisGraph, SynthesisResult


class CertifiedSynthesisSolver(ABC):
    """Common strategy contract for fair certified-synthesis comparisons."""

    @abstractmethod
    def solve(self, graph: CertifiedSynthesisGraph) -> SynthesisResult | None:
        """Return a certificate-backed solution or no solution within budget."""


class BranchAndBoundSolver(CertifiedSynthesisSolver):
    """Complete bounded enumeration baseline over the certified graph."""

    def __init__(self, max_stages: int = 6):
        self._max_stages = max_stages

    def solve(self, graph: CertifiedSynthesisGraph) -> SynthesisResult | None:
        return graph.solve(max_stages=self._max_stages)


class RouteFirstSolver(CertifiedSynthesisSolver):
    """Greedy route-first baseline that always takes the first valid edge."""

    def __init__(self, max_stages: int = 6):
        self._max_stages = max_stages

    def solve(self, graph: CertifiedSynthesisGraph) -> SynthesisResult | None:
        return graph.solve_greedy(max_stages=self._max_stages)


class RandomizedSearchSolver(CertifiedSynthesisSolver):
    """Seeded stochastic baseline for fixed-budget certified path sampling."""

    def __init__(self, seed: int, attempts: int = 32, max_stages: int = 6):
        if attempts < 1:
            raise ValueError("attempts must be positive")
        self._random = Random(seed)
        self._attempts = attempts
        self._max_stages = max_stages

    def solve(self, graph: CertifiedSynthesisGraph) -> SynthesisResult | None:
        best: SynthesisResult | None = None
        for _ in range(self._attempts):
            candidate = graph.solve_random(self._random, max_stages=self._max_stages)
            if candidate is not None and (best is None or candidate.score < best.score):
                best = candidate
        return best
