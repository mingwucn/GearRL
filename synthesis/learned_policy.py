"""Safe learned branch ordering for independently certified synthesis graphs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

from common.design_models import MeshEdge
from synthesis.certified_graph import CertifiedSynthesisGraph
from synthesis.policy_interface import CertifiedActionSpace


@dataclass(frozen=True)
class DemonstrationBatch:
    features: np.ndarray
    action_indices: np.ndarray


class CertifiedGraphFeatureEncoder:
    """Encode only certified graph state, never unvalidated geometry proposals."""

    FEATURE_DIMENSION = 5

    def encode(self, graph: CertifiedSynthesisGraph, stage_id: str, visited: set[str], max_actions: int) -> np.ndarray:
        stage = graph.stage(stage_id)
        output = graph.stage(graph.problem.output_stage_id)
        candidate_count = len(graph.candidates(stage_id, visited))
        distance = np.hypot(stage.center.x - output.center.x, stage.center.y - output.center.y)
        return np.asarray([
            stage.center.x / 1_000.0,
            stage.center.y / 1_000.0,
            distance / 1_000.0,
            len(visited) / max(1, len(graph.stages)),
            candidate_count / max_actions,
        ], dtype=np.float32)


class MaskedBranchOrderingNetwork(nn.Module):
    """Small MLP that scores an already-certified action index."""

    def __init__(self, feature_dimension: int, max_actions: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(feature_dimension, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU(), nn.Linear(32, max_actions)
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


class CertifiedDemonstrationCollector:
    """Extract action labels from certified deterministic solution paths."""

    def __init__(self, encoder: CertifiedGraphFeatureEncoder | None = None):
        self._encoder = encoder or CertifiedGraphFeatureEncoder()

    def collect(self, graph: CertifiedSynthesisGraph, max_actions: int) -> DemonstrationBatch:
        solution = graph.solve()
        if solution is None:
            return DemonstrationBatch(np.empty((0, self._encoder.FEATURE_DIMENSION), dtype=np.float32), np.empty(0, dtype=np.int64))
        action_space = CertifiedActionSpace(graph, max_actions)
        current = graph.problem.input_stage_id
        visited = {current}
        features: list[np.ndarray] = []
        labels: list[int] = []
        for edge in solution.train.meshes:
            candidates = action_space.candidates(current, visited)
            features.append(self._encoder.encode(graph, current, visited, max_actions))
            labels.append(candidates.index(edge))
            current = edge.driven_stage_id
            visited.add(current)
        return DemonstrationBatch(np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64))


class LearnedBranchOrderingPolicy:
    """Masked policy that can rank, but never create, certified transitions."""

    def __init__(self, max_actions: int, encoder: CertifiedGraphFeatureEncoder | None = None, device: str = "cpu"):
        if max_actions < 1:
            raise ValueError("max_actions must be positive")
        self.max_actions = max_actions
        self._encoder = encoder or CertifiedGraphFeatureEncoder()
        self._device = torch.device(device)
        self.network = MaskedBranchOrderingNetwork(self._encoder.FEATURE_DIMENSION, max_actions).to(self._device)

    def select(self, graph: CertifiedSynthesisGraph, stage_id: str, visited: set[str]) -> MeshEdge:
        action_space = CertifiedActionSpace(graph, self.max_actions)
        mask = torch.as_tensor(action_space.action_mask(stage_id, visited), device=self._device)
        if not bool(mask.any()):
            raise ValueError("No certified action is available")
        features = torch.as_tensor(self._encoder.encode(graph, stage_id, visited, self.max_actions), device=self._device).unsqueeze(0)
        with torch.no_grad():
            logits = self.network(features).squeeze(0)
            action = int(torch.argmax(logits.masked_fill(~mask, float("-inf"))).item())
        return action_space.select(stage_id, visited, action)


class BranchOrderingImitationTrainer:
    """Train a policy from deterministic certified traces before PPO refinement."""

    def __init__(self, policy: LearnedBranchOrderingPolicy, learning_rate: float = 1e-3):
        self._policy = policy
        self._optimizer = torch.optim.Adam(policy.network.parameters(), lr=learning_rate)
        self._loss = nn.CrossEntropyLoss()

    def train(self, batch: DemonstrationBatch, epochs: int = 20) -> float:
        if len(batch.features) == 0:
            raise ValueError("A non-empty certified demonstration batch is required")
        features = torch.as_tensor(batch.features, device=self._policy._device)
        labels = torch.as_tensor(batch.action_indices, device=self._policy._device)
        final_loss = 0.0
        self._policy.network.train()
        for _ in range(epochs):
            logits = self._policy.network(features)
            loss = self._loss(logits, labels)
            self._optimizer.zero_grad()
            loss.backward()
            self._optimizer.step()
            final_loss = float(loss.item())
        return final_loss


class PPOBranchRefinementTrainer:
    """Clipped policy-gradient refinement constrained by certified masks."""

    def __init__(self, policy: LearnedBranchOrderingPolicy, learning_rate: float = 3e-4, clip_epsilon: float = 0.2, gamma: float = 0.99):
        self._policy = policy
        self._optimizer = torch.optim.Adam(policy.network.parameters(), lr=learning_rate)
        self._clip_epsilon = clip_epsilon
        self._gamma = gamma

    def refine_episode(self, environment) -> float:
        state = environment.reset()
        transitions: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, float]] = []
        while not state.terminal:
            features = torch.as_tensor(state.features, device=self._policy._device).unsqueeze(0)
            mask = torch.as_tensor(state.action_mask, device=self._policy._device)
            logits = self._policy.network(features).squeeze(0).masked_fill(~mask, float("-inf"))
            distribution = torch.distributions.Categorical(logits=logits)
            action = distribution.sample()
            transitions.append((features, mask, action.detach(), distribution.log_prob(action).detach(), state.reward))
            state = environment.step(int(action.item()))
        returns = self._returns([reward for *_, reward in transitions] + [state.reward])
        loss = torch.tensor(0.0, device=self._policy._device)
        for (features, mask, action, old_log_prob, _), target in zip(transitions, returns):
            logits = self._policy.network(features).squeeze(0).masked_fill(~mask, float("-inf"))
            distribution = torch.distributions.Categorical(logits=logits)
            action_log_prob = distribution.log_prob(action)
            ratio = torch.exp(action_log_prob - old_log_prob)
            advantage = torch.as_tensor(target, device=self._policy._device)
            loss = loss - torch.minimum(ratio * advantage, torch.clamp(ratio, 1 - self._clip_epsilon, 1 + self._clip_epsilon) * advantage)
        self._optimizer.zero_grad()
        loss.backward()
        self._optimizer.step()
        return float(loss.item())

    def _returns(self, rewards: list[float]) -> list[float]:
        result: list[float] = []
        total = 0.0
        for reward in reversed(rewards):
            total = reward + self._gamma * total
            result.insert(0, total)
        return result
