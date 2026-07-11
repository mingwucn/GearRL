#!/usr/bin/env python3
"""Build or verify deterministic manuscript tables from frozen evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from reporting.artifact_registry import (
    CAEVerificationTable,
    LoadUncertaintyTable,
    PublicationArtifactRegistry,
    PublicationReproducer,
    SolverComparisonTable,
    StrengthCouplingTable,
)
from reporting.publication_figures import (
    FailureProbabilityFigure,
    SensitivityIndicesFigure,
    SolverComparisonFigure as SolverComparisonPlot,
    StrengthCouplingFigure,
)


class AEIPublicationTableFactory:
    """Declare the complete frozen-evidence table set for the AEI artifact."""

    def create(self):
        return (
            SolverComparisonTable(Path("data/results/requirements-comparison-v2/adjudication.json")),
            CAEVerificationTable(
                Path("data/results/cae-verification-v3/manifest.json"),
                Path("data/results/cae-verification-v3/summary.json"),
            ),
            LoadUncertaintyTable(
                Path("data/results/load-uncertainty-v1/manifest.json"),
                Path("data/results/load-uncertainty-v1/results.json"),
            ),
            StrengthCouplingTable(
                Path("data/results/strength-coupled-v1/manifest.json"),
                Path("data/results/strength-coupled-v1/summary.json"),
            ),
        )


class AEIPublicationFigureFactory:
    """Declare the complete evidence-derived AEI figure set."""

    def create(self):
        uncertainty_manifest = Path("data/results/load-uncertainty-v1/manifest.json")
        uncertainty_results = Path("data/results/load-uncertainty-v1/results.json")
        strength_manifest = Path("data/results/strength-coupled-v1/manifest.json")
        strength_summary = Path("data/results/strength-coupled-v1/summary.json")
        return (
            SolverComparisonPlot(Path("data/results/requirements-comparison-v2/adjudication.json")),
            FailureProbabilityFigure(uncertainty_manifest, uncertainty_results),
            SensitivityIndicesFigure(uncertainty_manifest, uncertainty_results),
            StrengthCouplingFigure(strength_manifest, strength_summary),
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
