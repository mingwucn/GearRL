#!/usr/bin/env python3
"""Run the predeclared solver scaling and anytime protocol."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.requirements_comparison import CpSatSolverFactory, DifferentialEvolutionFactory, ExactEnumeratorFactory
from evaluation.scaling import ScalingCaseFactory, ScalingEvidenceStore, ScalingProtocol, SolverScalingStudy
from run_strength_coupled_study import PredeclaredSolverViewRepository


class ScalingStudyCommand:
    def run(self, dataset: Path, output: Path, protocol: ScalingProtocol) -> Path:
        index, views = PredeclaredSolverViewRepository().load(dataset, ("valid-unit-30", "valid-nine-ten-30"))
        templates = {view.instance_id: view for view in views}
        cases = ScalingCaseFactory().create(templates, protocol)
        observations = SolverScalingStudy(
            (ExactEnumeratorFactory(), CpSatSolverFactory(), DifferentialEvolutionFactory()), protocol
        ).evaluate(cases)
        return ScalingEvidenceStore().write(output, protocol, index, cases, observations)


class ScalingStudyCLI:
    def run(self) -> None:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--dataset", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        arguments = parser.parse_args()
        print(ScalingStudyCommand().run(arguments.dataset, arguments.output, ScalingProtocol()))


if __name__ == "__main__":
    ScalingStudyCLI().run()
