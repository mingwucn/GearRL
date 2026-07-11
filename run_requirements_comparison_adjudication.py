"""Adjudicate a frozen-budget requirements-first solver comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark import CuratedBenchmarkLoader
from evaluation.requirements_comparison import RequirementsComparisonAdjudicator


class RequirementsComparisonAdjudicationCommand:
    def run(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("dataset", type=Path)
        parser.add_argument("comparison", type=Path)
        parser.add_argument("report", type=Path)
        arguments = parser.parse_args()
        dataset = CuratedBenchmarkLoader().load(arguments.dataset)
        adjudicator = RequirementsComparisonAdjudicator()
        report = adjudicator.adjudicate(dataset, arguments.comparison)
        print(adjudicator.write(report, arguments.report))


if __name__ == "__main__":
    RequirementsComparisonAdjudicationCommand().run()
