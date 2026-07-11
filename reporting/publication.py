"""Evidence-only publication tables for certified GearRL solver studies."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random
from statistics import median

from evaluation.comparison import SolverOutcome


@dataclass(frozen=True)
class MethodSummary:
    method: str
    observations: int
    correct_classification_rate: float
    median_runtime_s: float
    bootstrap_low: float
    bootstrap_high: float


class PublicationReportGenerator:
    """Summarize raw solver outcomes without accepting manually supplied metrics."""

    def summarize(self, outcomes: list[SolverOutcome], bootstrap_samples: int = 1_000, seed: int = 2026) -> list[MethodSummary]:
        if not outcomes or bootstrap_samples < 10:
            raise ValueError("Outcomes and at least ten bootstrap samples are required")
        grouped: dict[str, list[SolverOutcome]] = defaultdict(list)
        for outcome in outcomes:
            grouped[outcome.solver_name].append(outcome)
        random = Random(seed)
        summaries = []
        for method, records in sorted(grouped.items()):
            values = [float(record.correct_classification) for record in records]
            samples = sorted(sum(random.choice(values) for _ in values) / len(values) for _ in range(bootstrap_samples))
            summaries.append(MethodSummary(
                method,
                len(records),
                sum(values) / len(values),
                median(record.runtime_s for record in records),
                samples[int(bootstrap_samples * 0.025)],
                samples[int(bootstrap_samples * 0.975) - 1],
            ))
        return summaries

    def to_markdown(self, summaries: list[MethodSummary]) -> str:
        if not summaries:
            raise ValueError("At least one method summary is required")
        lines = [
            "| Method | N | Correct classification | 95% bootstrap CI | Median runtime (s) |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for summary in summaries:
            lines.append(
                f"| {summary.method} | {summary.observations} | {summary.correct_classification_rate:.3f} | "
                f"[{summary.bootstrap_low:.3f}, {summary.bootstrap_high:.3f}] | {summary.median_runtime_s:.6f} |"
            )
        return "\n".join(lines) + "\n"
