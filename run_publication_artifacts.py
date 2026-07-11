#!/usr/bin/env python3
"""Build or verify deterministic manuscript tables from frozen evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.artifact_registry import (
    AssemblyRobustnessTable,
    CAEQualificationTable,
    KnowledgeAblationTable,
    PlanetaryBaselineTable,
    PublicationArtifactRegistry,
    PublicationReproducer,
    SolverComparisonTable,
    SolverScalingTable,
    ReplayableProofTable,
    ToleranceAwareSelectionTable,
)
from reporting.publication_figures import (
    AssemblyRobustnessFigure,
    SolverComparisonFigure as SolverComparisonPlot,
    SolverScalingFigure,
)


class AEIPublicationTableFactory:
    """Declare the complete frozen-evidence table set for the AEI artifact."""

    def create(self):
        return (
            SolverComparisonTable(Path("data/results/requirements-comparison-v2/adjudication.json")),
            CAEQualificationTable(Path("data/results/cae-refinement-audit-v1/result.json")),
            KnowledgeAblationTable(
                Path("data/results/aei-knowledge-ablation-v1/manifest.json"),
                Path("data/results/aei-knowledge-ablation-v1/summary.json"),
            ),
            PlanetaryBaselineTable(
                Path("data/results/planetary-baseline-v1/manifest.json"),
                Path("data/results/planetary-baseline-v1/summary.json"),
            ),
            ReplayableProofTable(
                Path("data/results/replayable-negative-proofs-v1/manifest.json"),
                Path("data/results/replayable-negative-proofs-v1/summary.json"),
            ),
            ToleranceAwareSelectionTable(
                Path("data/results/tolerance-aware-selection-v1/manifest.json"),
                Path("data/results/tolerance-aware-selection-v1/summary.json"),
            ),
            SolverScalingTable(
                Path("data/results/scaling-v1/manifest.json"),
                Path("data/results/scaling-v1/summary.json"),
            ),
            AssemblyRobustnessTable(
                Path("data/results/assembly-robustness-confirmatory-v3/manifest.json"),
                Path("data/results/assembly-robustness-confirmatory-v3/summary.json"),
            ),
        )


class AEIPublicationFigureFactory:
    """Declare the complete evidence-derived AEI figure set."""

    def create(self):
        return (
            SolverComparisonPlot(Path("data/results/requirements-comparison-v2/adjudication.json")),
            SolverScalingFigure(
                Path("data/results/scaling-v1/manifest.json"),
                Path("data/results/scaling-v1/summary.json"),
            ),
            AssemblyRobustnessFigure(
                Path("data/results/assembly-robustness-confirmatory-v3/manifest.json"),
                Path("data/results/assembly-robustness-confirmatory-v3/summary.json"),
            ),
        )


class PublicationArtifactCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        action = parser.add_mutually_exclusive_group(required=True)
        action.add_argument("--output", type=Path)
        action.add_argument("--verify", type=Path)
        arguments = parser.parse_args()
        registry = PublicationArtifactRegistry()
        tables = AEIPublicationTableFactory().create()
        figures = AEIPublicationFigureFactory().create()
        if arguments.output:
            print(registry.build(arguments.output, tables, figures))
        else:
            PublicationReproducer(registry).verify_reproduction(arguments.verify, tables, figures)
            print(f"Verified byte-identical publication bundle: {arguments.verify}")


if __name__ == "__main__":
    PublicationArtifactCommand().run()
