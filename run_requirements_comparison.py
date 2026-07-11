"""Run frozen-budget solver comparison without evaluator evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark import SolverInputDirectoryLoader
from evaluation.requirements_comparison import (
    BlindRequirementsComparisonRunner,
    DifferentialEvolutionFactory,
    ExactEnumeratorFactory,
    RequirementsComparisonProtocol,
)


class RequirementsComparisonCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("solver_inputs", type=Path)
        parser.add_argument("output", type=Path)
        arguments = parser.parse_args()
        views = SolverInputDirectoryLoader().load(arguments.solver_inputs)
        runner = BlindRequirementsComparisonRunner(
            (ExactEnumeratorFactory(), DifferentialEvolutionFactory()),
            RequirementsComparisonProtocol(),
        )
        print(runner.run(views, arguments.output))


if __name__ == "__main__":
    RequirementsComparisonCommand().run()
