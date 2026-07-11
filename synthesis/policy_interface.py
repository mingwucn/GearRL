"""Action masking interface for learned branch ordering over certified graphs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.design_models import MeshEdge
from synthesis.certified_graph import CertifiedSynthesisGraph


@dataclass(frozen=True)
class CertifiedActionSpace:
    graph: CertifiedSynthesisGraph
    max_actions: int

    def __post_init__(self) -> None:
        if self.max_actions < 1:
            raise ValueError("max_actions must be positive")

    def candidates(self, stage_id: str, visited: set[str]) -> tuple[MeshEdge, ...]:
        edges = tuple(
            edge
            for edge in self.graph._outgoing.get(stage_id, [])
            if edge.driven_stage_id not in visited
        )
        if len(edges) > self.max_actions:
            raise ValueError("Candidate graph exceeds configured action capacity")
        return edges

    def action_mask(self, stage_id: str, visited: set[str]) -> np.ndarray:
        candidates = self.candidates(stage_id, visited)
        mask = np.zeros(self.max_actions, dtype=bool)
        mask[: len(candidates)] = True
        return mask

    def select(self, stage_id: str, visited: set[str], action_index: int) -> MeshEdge:
        candidates = self.candidates(stage_id, visited)
        if action_index < 0 or action_index >= len(candidates):
            raise ValueError("Policy selected a masked or unavailable action")
        return candidates[action_index]
