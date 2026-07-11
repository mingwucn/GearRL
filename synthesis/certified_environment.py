"""Masked reinforcement-learning environment for certified branch ordering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.design_models import MeshEdge
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.learned_policy import CertifiedGraphFeatureEncoder
from synthesis.policy_interface import CertifiedActionSpace


@dataclass(frozen=True)
class CertifiedTransition:
    features: np.ndarray
    action_mask: np.ndarray
    reward: float
    terminal: bool
    certificate_json: dict | None


class CertifiedBranchOrderingEnvironment:
    """Episode state that exposes only independently certified graph edges."""

    def __init__(self, graph: CertifiedSynthesisGraph, max_actions: int, encoder: CertifiedGraphFeatureEncoder | None = None):
        self._graph = graph
        self._actions = CertifiedActionSpace(graph, max_actions)
        self._encoder = encoder or CertifiedGraphFeatureEncoder()
        self._current: str = ""
        self._visited: set[str] = set()
        self._path: list[MeshEdge] = []

    def reset(self) -> CertifiedTransition:
        self._current = self._graph.problem.input_stage_id
        self._visited = {self._current}
        self._path = []
        return self._state(0.0, False, None)

    def step(self, action_index: int) -> CertifiedTransition:
        edge = self._actions.select(self._current, self._visited, action_index)
        self._path.append(edge)
        self._current = edge.driven_stage_id
        self._visited.add(self._current)
        if self._current != self._graph.problem.output_stage_id:
            if not self._actions.candidates(self._current, self._visited):
                return self._state(-100.0, True, None)
            return self._state(-0.1, False, None)
        certificate = self._graph.certify_path(self._path)
        return self._state(100.0 if certificate["valid"] else -100.0, True, certificate)

    def step_policy(self, policy) -> CertifiedTransition:
        """Advance one step using a masked policy without exposing private state."""
        edge = policy.select(self._graph, self._current, self._visited)
        action = self._actions.candidates(self._current, self._visited).index(edge)
        return self.step(action)

    def _state(self, reward: float, terminal: bool, certificate_json: dict | None) -> CertifiedTransition:
        if terminal:
            features = np.zeros(self._encoder.FEATURE_DIMENSION, dtype=np.float32)
            mask = np.zeros(self._actions.max_actions, dtype=bool)
        else:
            features = self._encoder.encode(self._graph, self._current, self._visited, self._actions.max_actions)
            mask = self._actions.action_mask(self._current, self._visited)
        return CertifiedTransition(features, mask, reward, terminal, certificate_json)
